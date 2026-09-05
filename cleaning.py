"""
Stage 3 — cleaning & normalisation.

Reads fare_observations, writes fare_observations_clean. Never deletes a
row: duplicates and outliers are flagged (is_duplicate / is_outlier), not
dropped, so the team can always answer "why is this fare missing from the
index" with a query instead of a shrug. See docs/DESIGN_hackathon_prototype.md §3.

Usage:
    python cleaning.py                 # process all rows not yet cleaned
    python cleaning.py --since 2026-09-01
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import text

from db import get_engine
from logging_setup import setup_logging

logger = setup_logging("sih26056.cleaning")

DEDUP_KEYS = ["source_tier", "origin", "destination", "departure_date", "airline", "hour_bucket"]
GROUP_KEYS = ["origin", "destination", "departure_date"]


def load_raw(since: str | None = None) -> pd.DataFrame:
    engine = get_engine()
    query = "SELECT * FROM fare_observations"
    params = {}
    if since:
        query += " WHERE observed_at_utc >= :since"
        params["since"] = since
    df = pd.read_sql(text(query), engine, params=params)
    logger.info("Loaded %d raw rows%s", len(df), f" since {since}" if since else "")
    return df


def flag_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        df["is_duplicate"] = pd.Series(dtype=bool)
        return df
    df = df.copy()
    df["observed_at_utc"] = pd.to_datetime(df["observed_at_utc"], utc=True)
    df["hour_bucket"] = df["observed_at_utc"].dt.floor("h")
    df["is_duplicate"] = df.duplicated(subset=DEDUP_KEYS, keep="first")
    n_dupes = int(df["is_duplicate"].sum())
    logger.info("Flagged %d/%d rows as duplicates", n_dupes, len(df))
    return df.drop(columns=["hour_bucket"])


def flag_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """IQR-based, per (origin, destination, departure_date) group.
    Rows with a null price, or a group too small to compute IQR
    meaningfully (<4 points), are never flagged -- absence of evidence
    isn't evidence of an outlier.
    """
    if df.empty:
        df["is_outlier"] = pd.Series(dtype=bool)
        return df

    df = df.copy()
    df["is_outlier"] = False

    def _flag_group(g: pd.DataFrame) -> pd.Series:
        prices = g["price"].dropna()
        if len(prices) < 4:
            return pd.Series(False, index=g.index)
        q1, q3 = prices.quantile(0.25), prices.quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        return (g["price"] < lower) | (g["price"] > upper)

    flags = df.groupby(GROUP_KEYS, group_keys=False).apply(_flag_group)
    df["is_outlier"] = flags.reindex(df.index).fillna(False)
    logger.info("Flagged %d/%d rows as price outliers", int(df["is_outlier"].sum()), len(df))
    return df


def interpolate_missing_cells(df: pd.DataFrame) -> pd.DataFrame:
    """
    STUB, deliberately not implemented.

    Missing-cell interpolation (e.g. "we have no observation for
    DEL-BLR at the 14-day window this hour, estimate one") is a
    methodology decision -- carry the last known value forward? linear
    interpolation across the booking-window curve? drop the cell from
    that run's index entirely? -- that the PRD explicitly defers to
    whoever owns index methodology (brief §8, item 7 territory).

    Guessing a policy here would let the index quietly compute numbers
    from data that doesn't exist. Raise instead of guessing.
    """
    raise NotImplementedError(
        "Missing-cell interpolation policy is not decided yet. "
        "index_calc.py computes from whatever cells ARE present and "
        "reports n_observations, rather than calling this function."
    )


def write_clean(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    engine = get_engine()
    df = df.copy()
    df["cleaned_at_utc"] = datetime.now(timezone.utc)
    # fare_observations_clean has its own id sequence (see schema.sql
    # comment) -- drop the raw table's id so Postgres assigns a fresh one
    # instead of colliding on a shared identity value.
    df = df.drop(columns=["id"], errors="ignore")
    df.to_sql("fare_observations_clean", engine, if_exists="append", index=False)
    logger.info("Wrote %d rows to fare_observations_clean", len(df))
    return len(df)


def run_once(since: str | None = None) -> int:
    df = load_raw(since=since)
    if df.empty:
        logger.info("No raw rows to clean.")
        return 0
    df = flag_duplicates(df)
    df = flag_outliers(df)
    return write_clean(df)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 3 cleaning")
    parser.add_argument("--since", help="ISO date/time, only clean rows observed after this")
    args = parser.parse_args()
    run_once(since=args.since)
