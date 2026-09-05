"""
Shared Postgres access for Stages 3-6 (cleaning, index, anomaly,
dashboard, API).

IMPORTANT: Stages 3-6 require Postgres. Stage 1-2 collectors can run in
CSV-only mode (see storage.py), but cleaning/index/anomaly/dashboard all
need to query across observations with SQL, so set DATABASE_URL before
running anything in this file's dependents:

    export DATABASE_URL="postgresql+psycopg2://user:pass@localhost:5432/airfare"
    psql "$DATABASE_URL" -f schema.sql   # once, to create the new tables too
"""
from __future__ import annotations

import sys

import config

if not config.DATABASE_URL:
    sys.stderr.write(
        "DATABASE_URL is not set. Stages 3-6 need Postgres (see this "
        "file's docstring). Stage 1/2 collectors can still run in "
        "CSV-only mode without this.\n"
    )

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        from sqlalchemy import create_engine
        if not config.DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set - see db.py docstring.")
        _engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
    return _engine
