"""
Shared storage layer for all tiers.

Design choice (brief §7, "Event log" + "Storage" rows): every tier writes
the SAME flat record shape into the SAME sink. Tier-specific quirks stay in
each tier's own collector; this module never branches on source_tier.

Default sink: append-only CSV (zero setup, works on day one).
Optional sink: Postgres/TimescaleDB if DATABASE_URL is set in config.py.

Record shape (one row = one fare observation):
    observed_at_utc      ISO8601 timestamp of the scrape
    source_tier          "tier0_dgca" | "tier1_google_flights" | "tier2_airline_direct"
    source_detail        e.g. "fast-flights" or "indigo_json_endpoint"
    origin, destination  IATA codes
    departure_date       ISO date the fare is FOR
    booking_window_days  departure_date - observed date, in days
    airline               carrier name/code, "" if unknown (e.g. Tier 0 band)
    fare_type            e.g. "economy", "saver", "flexi" — best-effort
    price                numeric, INR unless noted
    currency             default "INR"
    is_price_band        True for Tier 0 (a band, not a transacted price)
    raw_ref               short pointer back to the raw payload/log offset,
                          NOT the raw HTML/JSON itself (brief §5.2: "store
                          observations, not pages")
"""
from __future__ import annotations

import csv
import logging
import os
from dataclasses import dataclass, asdict, fields
from datetime import datetime, timezone
from typing import Optional

import config

logger = logging.getLogger("sih26056.storage")


@dataclass
class FareObservation:
    observed_at_utc: str
    source_tier: str
    source_detail: str
    origin: str
    destination: str
    departure_date: str
    booking_window_days: int
    airline: str
    fare_type: str
    price: Optional[float]
    currency: str = "INR"
    is_price_band: bool = False
    raw_ref: str = ""

    @staticmethod
    def now_utc_iso() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")


CSV_FIELDNAMES = [f.name for f in fields(FareObservation)]


def _ensure_csv_header(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_FIELDNAMES)
            writer.writeheader()


def write_csv(rows: list[FareObservation], path: str = config.CSV_PATH) -> int:
    if not rows:
        return 0
    _ensure_csv_header(path)
    with open(path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDNAMES)
        for r in rows:
            writer.writerow(asdict(r))
    logger.info("Wrote %d rows to CSV %s", len(rows), path)
    return len(rows)


_pg_engine = None


def _get_pg_engine():
    global _pg_engine
    if _pg_engine is None:
        from sqlalchemy import create_engine
        _pg_engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
    return _pg_engine


def write_postgres(rows: list[FareObservation]) -> int:
    if not rows:
        return 0
    from sqlalchemy import text

    engine = _get_pg_engine()
    insert_sql = text(
        """
        INSERT INTO fare_observations
            (observed_at_utc, source_tier, source_detail, origin, destination,
             departure_date, booking_window_days, airline, fare_type, price,
             currency, is_price_band, raw_ref)
        VALUES
            (:observed_at_utc, :source_tier, :source_detail, :origin, :destination,
             :departure_date, :booking_window_days, :airline, :fare_type, :price,
             :currency, :is_price_band, :raw_ref)
        """
    )
    with engine.begin() as conn:
        conn.execute(insert_sql, [asdict(r) for r in rows])
    logger.info("Wrote %d rows to Postgres", len(rows))
    return len(rows)


def persist(rows: list[FareObservation]) -> int:
    """Single entry point every collector should call."""
    if config.DATABASE_URL:
        return write_postgres(rows)
    return write_csv(rows)
