"""
SIH26056 — Phase 1 collector configuration.

Everything a teammate would plausibly want to tune lives here, not
scattered through collector.py, so the "one thing to do today" stays a
one-file review before a hand-off.
"""
import os
from dotenv import load_dotenv

load_dotenv()  # picks up a local .env if present; harmless if it isn't

# --- Routes (Tier 1 backbone, per brief §7 "Phase 1" and §6.2) -------------
# (origin, destination) IATA codes. Kept to the three the brief names so the
# very first run finishes fast; add more once this is stable.
ROUTES = [
    ("DEL", "BOM"),
    ("BOM", "BLR"),
    ("DEL", "BLR"),
]

# --- Booking windows ---------------------------------------------------
# Days-ahead-of-search departure offsets to sample each run. This gives the
# index methodology team a booking-window dimension from day one instead of
# only "cheapest fare today", which the brief flags (§8, item 7) as an open
# question they still need to settle.
BOOKING_WINDOWS_DAYS = [3, 7, 14, 30]

# --- Query parameters ----------------------------------------------------
SEAT_CLASS = "economy"          # economy | premium-economy | business | first
TRIP_TYPE = "one-way"
ADULTS = 1

# --- Politeness / throttling (brief §3.2) ---------------------------------
# Tier 1 (plain HTTP, no browser) is low-risk, but we still space calls out:
# a slow collector that never gets throttled beats a fast one that does.
MIN_DELAY_SECONDS = 4
MAX_DELAY_SECONDS = 9
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 20        # exponential backoff base on failure

# --- Storage ---------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CSV_PATH = os.path.join(DATA_DIR, "fare_observations.csv")

# If set (e.g. postgresql+psycopg2://user:pass@host:5432/airfare), the
# collector writes to Postgres/TimescaleDB instead of CSV. Unset = CSV.
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip() or None

# --- Identification (brief §5.2 "Identify ourselves") ----------------------
PROJECT_USER_AGENT_NOTE = (
    "SIH26056-airfare-index-prototype "
    "(non-commercial, MoSPI hackathon PoC; contact: <team-email-here>)"
)

# --- Logging ---------------------------------------------------------------
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "collector.log")
