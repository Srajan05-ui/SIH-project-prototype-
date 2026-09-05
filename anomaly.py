"""
Stage 5 — anomaly detection & alerts.

Default method: rolling z-score per route (works with days of data).
Optional: Isolation Forest, if scikit-learn is installed and METHOD is
switched -- see docs/TECH_STACK_hackathon_prototype.md for why z-score is
the default rather than Isolation Forest/Prophet at hackathon data
volumes.

Usage:
    python anomaly.py                       # scan real clean data, log alerts
    python anomaly.py --inject-test-anomaly  # PROVE the detector works:
                                              # adds one synthetic spike to
                                              # an in-memory copy only,
                                              # never written to the DB.
"""
from __future__ import annotations

import argparse

import pandas as pd
from sqlalchemy import text

from db import get_engine
from logging_setup import setup_logging

logger = setup_logging("sih26056.anomaly")

METHOD = "zscore"          # "zscore" | "isolation_forest"
ROLLING_WINDOW = 10
ZSCORE_THRESHOLD = 2.5


def load_clean() -> pd.DataFrame:
    engine = get_engine()
    query = """
        SELECT * FROM fare_observations_clean
        WHERE is_duplicate = FALSE AND is_outlier = FALSE AND price IS NOT NULL
        ORDER BY origin, destination, observed_at_utc
    """
    df = pd.read_sql(text(query), engine)
    df["observed_at_utc"] = pd.to_datetime(df["observed_at_utc"], utc=True)
    return df


def _inject_test_anomaly(df: pd.DataFrame) -> pd.DataFrame:
    """Adds ONE synthetic high-price row to an in-memory copy so the team
    can demo the detector without waiting for a real spike or faking real
    data in the actual table. Never persisted."""
    if df.empty:
        logger.warning("No real data loaded -- cannot inject a test anomaly on top of nothing.")
        return df
    df = df.copy()
    sample_row = df.iloc[-1].copy()
    sample_row["price"] = (df["price"].mean() or 1000) * 5  # obviously extreme
    sample_row["observed_at_utc"] = pd.Timestamp.utcnow()
    sample_row["source_detail"] = "SYNTHETIC_TEST_ROW_NOT_REAL"
    df = pd.concat([df, sample_row.to_frame().T], ignore_index=True)
    logger.info(
        "Injected 1 synthetic test row for %s->%s at price=%.0f (in-memory only, not written to DB)",
        sample_row["origin"], sample_row["destination"], sample_row["price"],
    )
    return df


def detect_zscore(df: pd.DataFrame) -> pd.DataFrame:
    flagged = []
    for (origin, destination), g in df.groupby(["origin", "destination"]):
        g = g.sort_values("observed_at_utc").reset_index(drop=True)
        rolling_mean = g["price"].rolling(ROLLING_WINDOW, min_periods=3).mean()
        rolling_std = g["price"].rolling(ROLLING_WINDOW, min_periods=3).std()
        z = (g["price"] - rolling_mean) / rolling_std
        anomalies = g[z.abs() > ZSCORE_THRESHOLD]
        for _, row in anomalies.iterrows():
            flagged.append(row)
    return pd.DataFrame(flagged)


def detect_isolation_forest(df: pd.DataFrame) -> pd.DataFrame:
    try:
        from sklearn.ensemble import IsolationForest
    except ImportError as exc:
        raise RuntimeError(
            "scikit-learn not installed. `pip install scikit-learn` or "
            "set METHOD = 'zscore' in anomaly.py."
        ) from exc

    flagged = []
    for (origin, destination), g in df.groupby(["origin", "destination"]):
        if len(g) < 10:
            logger.info("Skipping IsolationForest for %s->%s: too few points (%d)", origin, destination, len(g))
            continue
        model = IsolationForest(contamination=0.05, random_state=42)
        preds = model.fit_predict(g[["price"]])
        flagged.append(g[preds == -1])
    return pd.concat(flagged, ignore_index=True) if flagged else pd.DataFrame()


def run_once(inject_test_anomaly: bool = False) -> pd.DataFrame:
    df = load_clean()
    if inject_test_anomaly:
        df = _inject_test_anomaly(df)

    if df.empty:
        logger.info("No data to scan for anomalies.")
        return pd.DataFrame()

    if METHOD == "isolation_forest":
        flagged = detect_isolation_forest(df)
    else:
        flagged = detect_zscore(df)

    if flagged.empty:
        logger.info("No anomalies detected (method=%s).", METHOD)
    else:
        for _, row in flagged.iterrows():
            logger.warning(
                "ALERT: possible fare anomaly | %s->%s | price=%.0f INR | source=%s | observed=%s",
                row["origin"], row["destination"], row["price"], row["source_detail"], row["observed_at_utc"],
            )
    return flagged


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 5 anomaly detection")
    parser.add_argument(
        "--inject-test-anomaly", action="store_true",
        help="add one synthetic spike (in-memory only) to prove the detector works",
    )
    args = parser.parse_args()
    run_once(inject_test_anomaly=args.inject_test_anomaly)
