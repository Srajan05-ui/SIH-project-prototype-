"""
Tier 1 collector — Google Flights protobuf query via `fast-flights`.

This is the always-on backbone (brief §0, §6.2, §7 "Phase 1"). Plain HTTP,
no browser, no API key, low anti-bot difficulty. Run this hourly.

Usage:
    python collector_tier1.py                 # one pass, all routes x windows
    python collector_tier1.py --loop           # loop forever, hourly
    python collector_tier1.py --route DEL BOM --window 7   # single query, for testing

IMPORTANT — verify before relying on this in the deck:
`fast-flights`' public API has changed across versions before (the brief
flags this explicitly: "Google can change the format at any time"). The
import names and Result object shape below match the commonly published
`fast-flights` API as of its last stable releases. Before the first real
run:
    pip install fast-flights
    python -c "from fast_flights import FlightData, Passengers, get_flights; print('ok')"
If that import fails, open the installed package and adjust the three
lines marked `# FAST-FLIGHTS API` below to match — the rest of this file
(throttling, retry, storage) does not need to change.
"""
from __future__ import annotations

import argparse
import random
import time
from datetime import date, datetime, timedelta, timezone

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import config
from logging_setup import setup_logging
from storage import FareObservation, persist

logger = setup_logging("sih26056.tier1")


class FetchError(Exception):
    pass


@retry(
    reraise=True,
    stop=stop_after_attempt(config.MAX_RETRIES),
    wait=wait_exponential(multiplier=config.BACKOFF_BASE_SECONDS, min=config.BACKOFF_BASE_SECONDS, max=300),
    retry=retry_if_exception_type(FetchError),
)
def _query_google_flights(origin: str, destination: str, departure_date: date):
    # FAST-FLIGHTS API -----------------------------------------------------
    from fast_flights import FlightQuery, Passengers, get_flights, create_query

    try:
        query = create_query(
            flights=[
                FlightQuery(
                    date=departure_date.isoformat(),
                    from_airport=origin,
                    to_airport=destination,
                )
            ],
            trip=config.TRIP_TYPE,
            seat=config.SEAT_CLASS,
            passengers=Passengers(
                adults=config.ADULTS, children=0, infants_in_seat=0, infants_on_lap=0
            ),
            currency="INR",
        )
        result = get_flights(query)
    except Exception as exc:  # noqa: BLE001 - we deliberately convert to FetchError for retry
        raise FetchError(f"{origin}->{destination} on {departure_date}: {exc}") from exc
    # ------------------------------------------------------------------------
    return result


def _to_observations(result, origin: str, destination: str, departure_date: date) -> list[FareObservation]:
    observed_at = FareObservation.now_utc_iso()
    booking_window = (departure_date - date.today()).days
    rows: list[FareObservation] = []

    flights = result if isinstance(result, list) else (getattr(result, "flights", None) or [])
    if not flights:
        logger.warning("No flights parsed for %s->%s on %s (page structure may have changed)",
                        origin, destination, departure_date)
        return rows

    for f in flights:
        # Field names per common fast-flights Flight object; adjust if your
        # installed version differs (see module docstring).
        price_raw = getattr(f, "price", None)
        price = _parse_price(price_raw)
        # ── PERMANENT USD GUARD ──────────────────────────────────────────────
        # Converts suspiciously-low prices that indicate Google returned USD
        # instead of INR (happens on US-located cloud servers).
        price = _sanitise_price(price, origin, destination)
        # ─────────────────────────────────────────────────────────────────────
        airlines = getattr(f, "airlines", [])
        airline = airlines[0] if airlines else (getattr(f, "name", "") or getattr(f, "airline", "") or "")

        rows.append(
            FareObservation(
                observed_at_utc=observed_at,
                source_tier="tier1_google_flights",
                source_detail="fast-flights",
                origin=origin,
                destination=destination,
                departure_date=departure_date.isoformat(),
                booking_window_days=booking_window,
                airline=airline,
                fare_type=config.SEAT_CLASS,
                price=price,
                currency="INR",
                is_price_band=False,
                raw_ref=f"{origin}{destination}_{departure_date.isoformat()}_{observed_at}",
            )
        )
    return rows


# Minimum realistic economy fare on ANY Indian domestic route (INR).
# No seat exists below this — if we get a value lower, it is USD from a
# US-located cloud server. We convert it using a conservative rate.
_MIN_INR_PRICE = 500
_USD_TO_INR_APPROX = 84.0   # update yearly if needed


def _parse_price(price_raw) -> float | None:
    if price_raw is None:
        return None
    if isinstance(price_raw, (int, float)):
        return float(price_raw)
    # fast-flights often returns a formatted string like "₹4,521" or "$93"
    # Strip all non-numeric characters except decimal point
    digits = "".join(ch for ch in str(price_raw) if ch.isdigit() or ch == ".")
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


def _sanitise_price(price: float | None, origin: str, destination: str) -> float | None:
    """Permanent USD guard.

    Google Flights on US-based servers (GitHub Actions) sometimes ignores the
    currency='INR' parameter and returns prices in USD.  No legitimate Indian
    domestic economy fare is below _MIN_INR_PRICE (Rs 500).  If we receive a
    price below that floor we assume it is USD and convert it.  A log WARNING
    is emitted every time so the issue is always visible in the pipeline logs.
    """
    if price is None:
        return None
    if price < _MIN_INR_PRICE:
        converted = round(price * _USD_TO_INR_APPROX)
        logger.warning(
            "CURRENCY GUARD triggered for %s->%s: received %.0f (looks like USD). "
            "Converting to INR: %.0f x %.0f = %.0f INR",
            origin, destination, price, price, _USD_TO_INR_APPROX, converted,
        )
        return float(converted)
    return price


def run_once(routes=None, windows=None) -> int:
    routes = routes or config.ROUTES
    windows = windows or config.BOOKING_WINDOWS_DAYS
    total_written = 0

    for origin, destination in routes:
        for window_days in windows:
            departure_date = date.today() + timedelta(days=window_days)
            try:
                result = _query_google_flights(origin, destination, departure_date)
                rows = _to_observations(result, origin, destination, departure_date)
                total_written += persist(rows)
                logger.info("OK %s->%s +%dd: %d fares", origin, destination, window_days, len(rows))
            except FetchError as exc:
                logger.error("FAILED after retries: %s", exc)
                # Per brief §3.2: on repeated failure, move on rather than
                # hammering a source that is telling us no.
                continue
            finally:
                # Politeness delay (brief §3.2) even though Tier 1 is low-risk.
                time.sleep(random.uniform(config.MIN_DELAY_SECONDS, config.MAX_DELAY_SECONDS))

    logger.info("Pass complete. %d observations written.", total_written)
    return total_written


def loop_hourly():
    logger.info("Starting hourly loop. Ctrl+C to stop.")
    while True:
        started = datetime.now(timezone.utc)
        try:
            run_once()
        except Exception:  # noqa: BLE001 - a single bad pass must not kill the loop
            logger.exception("Unhandled error in collection pass; will retry next hour.")
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        sleep_for = max(0, 3600 - elapsed)
        logger.info("Sleeping %.0fs until next pass.", sleep_for)
        time.sleep(sleep_for)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tier 1 Google Flights collector")
    parser.add_argument("--loop", action="store_true", help="run forever, hourly")
    parser.add_argument("--route", nargs=2, metavar=("ORIGIN", "DEST"), help="single route override")
    parser.add_argument("--window", type=int, help="single booking-window-days override")
    args = parser.parse_args()

    routes = [tuple(args.route)] if args.route else None
    windows = [args.window] if args.window else None

    if args.loop:
        loop_hourly()
    else:
        run_once(routes=routes, windows=windows)
