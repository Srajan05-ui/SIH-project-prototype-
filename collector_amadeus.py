"""
Tier 1 collector — Amadeus API flight search.

This uses the official Amadeus Python SDK to fetch real-time flight offers.
It finds the cheapest available flight per airline for the specified routes and windows.

Usage:
    python collector_amadeus.py                 # one pass, all routes x windows
    python collector_amadeus.py --loop          # loop forever, hourly
    python collector_amadeus.py --route DEL BOM --window 7   # single query, for testing
"""
from __future__ import annotations

import argparse
import os
import random
import time
from datetime import date, datetime, timedelta, timezone

from amadeus import Client, ResponseError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import config
from logging_setup import setup_logging
from storage import FareObservation, persist

logger = setup_logging("sih26056.amadeus")

# Initialize Amadeus Client
# Credentials should be set in .env or system environment variables
amadeus = Client(
    client_id=os.environ.get("AMADEUS_API_KEY", ""),
    client_secret=os.environ.get("AMADEUS_API_SECRET", ""),
    # By default, this hits the 'test' environment. 
    # Pass hostname='production' when ready for live data.
)

class FetchError(Exception):
    pass


@retry(
    reraise=True,
    stop=stop_after_attempt(config.MAX_RETRIES),
    wait=wait_exponential(multiplier=config.BACKOFF_BASE_SECONDS, min=config.BACKOFF_BASE_SECONDS, max=300),
    retry=retry_if_exception_type(FetchError),
)
def _query_amadeus(origin: str, destination: str, departure_date: date):
    try:
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=departure_date.isoformat(),
            adults=config.ADULTS,
            travelClass=config.SEAT_CLASS.upper(),
            currencyCode="INR",
            max=50  # Get up to 50 results to find different airlines
        )
        return response.data
    except ResponseError as exc:
        raise FetchError(f"{origin}->{destination} on {departure_date}: {exc}") from exc


def _to_observations(data, origin: str, destination: str, departure_date: date) -> list[FareObservation]:
    observed_at = FareObservation.now_utc_iso()
    booking_window = (departure_date - date.today()).days
    rows: list[FareObservation] = []

    if not data:
        logger.warning("No flights returned for %s->%s on %s", origin, destination, departure_date)
        return rows

    # We want the cheapest flight per airline
    cheapest_per_airline = {}

    for offer in data:
        # Get price
        try:
            price = float(offer['price']['total'])
        except (KeyError, ValueError):
            continue

        # Get validating airline
        try:
            validating_airlines = offer.get('validatingAirlineCodes', [])
            airline_code = validating_airlines[0] if validating_airlines else "UNKNOWN"
        except (KeyError, IndexError):
            airline_code = "UNKNOWN"

        # Update if it's the cheapest we've seen for this airline
        if airline_code not in cheapest_per_airline or price < cheapest_per_airline[airline_code]['price']:
            cheapest_per_airline[airline_code] = {
                'price': price,
                'offer_id': offer.get('id', 'unknown')
            }

    for airline, details in cheapest_per_airline.items():
        rows.append(
            FareObservation(
                observed_at_utc=observed_at,
                source_tier="tier1_amadeus_api",
                source_detail="amadeus_sdk",
                origin=origin,
                destination=destination,
                departure_date=departure_date.isoformat(),
                booking_window_days=booking_window,
                airline=airline,
                fare_type=config.SEAT_CLASS,
                price=details['price'],
                currency="INR",
                is_price_band=False,
                raw_ref=f"amadeus_{details['offer_id']}_{observed_at}",
            )
        )
    return rows


def run_once(routes=None, windows=None) -> int:
    routes = routes or config.ROUTES
    windows = windows or config.BOOKING_WINDOWS_DAYS
    total_written = 0
    
    if not os.environ.get("AMADEUS_API_KEY") or os.environ.get("AMADEUS_API_KEY") == "your_amadeus_api_key_here":
        logger.error("AMADEUS_API_KEY is not set. Cannot run collector.")
        return 0

    for origin, destination in routes:
        for window_days in windows:
            departure_date = date.today() + timedelta(days=window_days)
            try:
                data = _query_amadeus(origin, destination, departure_date)
                rows = _to_observations(data, origin, destination, departure_date)
                total_written += persist(rows)
                logger.info("OK %s->%s +%dd: %d airlines found", origin, destination, window_days, len(rows))
            except FetchError as exc:
                logger.error("FAILED after retries: %s", exc)
                continue
            finally:
                # Politeness delay between API calls
                time.sleep(random.uniform(config.MIN_DELAY_SECONDS, config.MAX_DELAY_SECONDS))

    logger.info("Pass complete. %d observations written.", total_written)
    return total_written


def loop_hourly():
    logger.info("Starting hourly loop. Ctrl+C to stop.")
    while True:
        started = datetime.now(timezone.utc)
        try:
            run_once()
        except Exception:
            logger.exception("Unhandled error in collection pass; will retry next hour.")
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        sleep_for = max(0, 3600 - elapsed)
        logger.info("Sleeping %.0fs until next pass.", sleep_for)
        time.sleep(sleep_for)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Amadeus API flight fare collector")
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
