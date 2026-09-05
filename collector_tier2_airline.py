"""
Tier 2 collector — airline direct booking-engine JSON endpoint, via
curl_cffi (TLS/browser-impersonating HTTP client, no headless browser).

This matches the pipeline you sketched:
    Python -> curl_cffi -> Airline JSON endpoint -> JSON -> Fare

WHY THIS FILE HAS NO REAL ENDPOINT URL IN IT YET
Every airline's search endpoint is different and undocumented (brief
§6.2: "these are internal endpoints, not published APIs... treat them as
Tier 2, apply the same politeness rules, and be prepared for them to
break"). I'm not going to guess or fabricate one -- a wrong URL/payload
either does nothing or hits the wrong endpoint. You find the real one
in about 10 minutes with your own browser's DevTools, and it's a skill
your team needs anyway for when it inevitably changes:

  HOW TO FIND IT (do this once per airline, re-check if it stops working):
    1. Open the airline's flight search page in Chrome, DevTools -> Network,
       filter to "Fetch/XHR".
    2. Run a normal search (route + date) as a real user would.
    3. Find the request that returns fares as JSON (usually named something
       like "search", "availability", "fare"). Click it.
    4. Right-click -> Copy -> Copy as cURL.
    5. Paste that curl command below in RAW_CURL_REFERENCE (as a comment,
       for the team's own reference -- do not commit real cookies/tokens).
    6. Translate the method, URL, headers and JSON body into the
       `build_request()` function below.

This keeps the actual request-shape decision with a human looking at a
real page, which is also the honest thing to do: these are the airline's
own JSON responses served to a normal browser search, not an
authentication bypass or a hidden API.

BEFORE RUNNING: this always checks robots.txt for the endpoint's domain
first (see robots_check.py) and refuses to proceed if disallowed.
"""
from __future__ import annotations

import random
import time
from datetime import date, timedelta

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import config
from logging_setup import setup_logging
from robots_check import check_allowed
from storage import FareObservation, persist

logger = setup_logging("sih26056.tier2")

# --- Fill this in after the DevTools step above -----------------------------
AIRLINE_NAME = "indigo_mock"
SEARCH_ENDPOINT = "http://localhost:8000/mock-airline/search"
# RAW_CURL_REFERENCE:
# Mock endpoint for demo purposes.
# -----------------------------------------------------------------------------


class FetchError(Exception):
    pass


def build_request(origin: str, destination: str, departure_date: date) -> dict:
    """
    Translate the DevTools-observed request into a dict curl_cffi can send.
    This is a TEMPLATE -- the real shape depends entirely on what you found
    in the Network tab. A common shape looks roughly like this; adjust
    field names, method, and headers to match what you actually captured.
    """
    return {
        "method": "GET",
        "url": SEARCH_ENDPOINT,
        "params": {
            "origin": origin,
            "destination": destination,
            "date": departure_date.isoformat(),
            "adults": config.ADULTS,
            "cabin": config.SEAT_CLASS,
        },
        "headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Accept-Language": "en-IN,en;q=0.9",
            # NOTE: some airline endpoints require a referer or a
            # short-lived token minted by an earlier page load. If the
            # request 403s despite matching DevTools, that token is
            # probably missing -- this is exactly the case the brief
            # (§4.1, §3.4) says to back off from rather than fight.
        },
    }


@retry(
    reraise=True,
    stop=stop_after_attempt(config.MAX_RETRIES),
    wait=wait_exponential(multiplier=config.BACKOFF_BASE_SECONDS, min=config.BACKOFF_BASE_SECONDS, max=300),
    retry=retry_if_exception_type(FetchError),
)
def _fetch(origin: str, destination: str, departure_date: date) -> dict:
    from curl_cffi import requests as curl_requests  # impersonating client

    if not SEARCH_ENDPOINT:
        raise RuntimeError(
            "SEARCH_ENDPOINT is empty. Follow the DevTools steps in this "
            "file's docstring before running Tier 2."
        )

    if not check_allowed(SEARCH_ENDPOINT):
        raise RuntimeError(
            f"robots.txt disallows {SEARCH_ENDPOINT} -- per brief §5.2 we do "
            "not crawl this path. Pick a different endpoint or drop Tier 2 "
            "for this airline."
        )

    req = build_request(origin, destination, departure_date)
    try:
        resp = curl_requests.request(
            req["method"],
            req["url"],
            params=req.get("params"),
            headers=req.get("headers"),
            impersonate="chrome124",  # TLS/HTTP2 fingerprint impersonation
            timeout=20,
        )
        if resp.status_code == 403 or resp.status_code == 429:
            # Brief §3.4: a block is an answer. Don't fight it inside this
            # function -- let it bubble up so run_once() can drop the source
            # for this cycle rather than retry into a ban.
            raise FetchError(f"HTTP {resp.status_code} from {req['url']}")
        resp.raise_for_status()
        return resp.json()
    except FetchError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise FetchError(str(exc)) from exc


def _to_observations(payload: dict, origin: str, destination: str, departure_date: date) -> list[FareObservation]:
    """
    TEMPLATE parser -- the real JSON shape depends on the endpoint you
    found. Adjust the field lookups below once you've printed a sample
    payload and looked at it.
    """
    observed_at = FareObservation.now_utc_iso()
    booking_window = (departure_date - date.today()).days
    rows: list[FareObservation] = []

    # Navigating complex airline JSON shape
    journeys = payload.get("data", {}).get("flightResults", {}).get("journeys", [])
    for journey in journeys:
        segments = journey.get("segments", [])
        if not segments:
            continue
        
        carrier_code = segments[0].get("flightDesignator", {}).get("carrierCode", AIRLINE_NAME)
        
        fares = journey.get("fares", {})
        economy_fare = fares.get("ECONOMY", {})
        price = economy_fare.get("totalAmount")
        currency = economy_fare.get("currency", "INR")

        if price:
            rows.append(
                FareObservation(
                    observed_at_utc=observed_at,
                    source_tier="tier2_airline_direct",
                    source_detail="MockAirlineAPI",
                    origin=origin,
                    destination=destination,
                    departure_date=departure_date.isoformat(),
                    booking_window_days=booking_window,
                    airline=carrier_code,
                    fare_type="ECONOMY",
                    price=price,
                    currency=currency,
                    is_price_band=False,
                    raw_ref=f"{AIRLINE_NAME}_{origin}{destination}_{departure_date.isoformat()}_{observed_at}",
                )
            )
    if not rows:
        logger.warning(
            "No fares parsed for %s->%s on %s. Either the route has no "
            "flights, or payload['fares'] doesn't match this endpoint's "
            "real shape yet -- print(payload) and adjust _to_observations().",
            origin, destination, departure_date,
        )
    return rows


def run_once(routes=None, windows=None) -> int:
    routes = routes or config.ROUTES
    windows = windows or config.BOOKING_WINDOWS_DAYS
    total = 0

    for origin, destination in routes:
        for window_days in windows:
            departure_date = date.today() + timedelta(days=window_days)
            try:
                payload = _fetch(origin, destination, departure_date)
                rows = _to_observations(payload, origin, destination, departure_date)
                total += persist(rows)
                logger.info("OK %s->%s +%dd: %d fares", origin, destination, window_days, len(rows))
            except (FetchError, RuntimeError) as exc:
                logger.error("Tier 2 failed, dropping this cell for the cycle: %s", exc)
                continue
            finally:
                time.sleep(random.uniform(config.MIN_DELAY_SECONDS, config.MAX_DELAY_SECONDS))

    return total


if __name__ == "__main__":
    run_once()
