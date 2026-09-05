"""
Stage 4 — Airfare Price Index computation.

Route-level only for this prototype (see docs/PRD_hackathon_prototype.md
§3 and docs/DESIGN_hackathon_prototype.md §4 for why category/national
rollup and seasonal adjustment are out of scope here).

Formula (fixed-basket Laspeyres-style, single item = the route):
    index_value(route, t) = 100 * price(route, t) / price(route, base_period)

- price(route, t)            = mean of non-duplicate, non-outlier prices
                                for that route in the current run
- price(route, base_period)  = mean of non-duplicate, non-outlier prices
                                for that route on the EARLIEST date with
                                cleaned data for that route

Usage:
    python index_calc.py
"""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import text

from db import get_engine
from logging_setup import setup_logging

logger = setup_logging("sih26056.index_calc")


def load_clean() -> pd.DataFrame:
    engine = get_engine()
    query = """
        SELECT * FROM fare_observations_clean
        WHERE is_duplicate = FALSE AND is_outlier = FALSE AND price IS NOT NULL
    """
    df = pd.read_sql(text(query), engine)
    df["observed_at_utc"] = pd.to_datetime(df["observed_at_utc"], utc=True)
    logger.info("Loaded %d clean, non-outlier rows for index computation", len(df))
    return df


def compute_route_index(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        logger.warning("No clean data available -- nothing to index.")
        return pd.DataFrame()

    rows = []
    computed_at = datetime.now(timezone.utc)

    for (origin, destination), g in df.groupby(["origin", "destination"]):
        g = g.sort_values("observed_at_utc")
        base_date = g["observed_at_utc"].dt.date.min()
        base_slice = g[g["observed_at_utc"].dt.date == base_date]
        base_price = base_slice["price"].mean()

        current_price = g["price"].mean()  # whole loaded window as "current"

        if pd.isna(base_price) or base_price == 0:
            logger.warning("Skipping %s->%s: no usable base price", origin, destination)
            continue

        index_value = 100.0 * current_price / base_price
        rows.append(
            {
                "computed_at_utc": computed_at,
                "origin": origin,
                "destination": destination,
                "base_period": base_date,
                "index_value": round(index_value, 4),
                "n_observations": int(len(g)),
            }
        )
        logger.info(
            "%s->%s: index=%.2f (base %.0f INR on %s, current %.0f INR, n=%d)",
            origin, destination, index_value, base_price, base_date, current_price, len(g),
        )

    return pd.DataFrame(rows)


def write_index(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    engine = get_engine()
    df.to_sql("airfare_index", engine, if_exists="append", index=False)
    logger.info("Wrote %d index rows to airfare_index", len(df))
    return len(df)


def run_once() -> int:
    df = load_clean()
    index_df = compute_route_index(df)
    return write_index(index_df)


if __name__ == "__main__":
    run_once()
