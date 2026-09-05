-- SIH26056 fare_observations schema.
-- Only needed if you set DATABASE_URL; CSV works with zero setup.
-- Run manually once: psql "$DATABASE_URL" -f schema.sql

CREATE TABLE IF NOT EXISTS fare_observations (
    id                    BIGSERIAL PRIMARY KEY,
    observed_at_utc       TIMESTAMPTZ NOT NULL,
    source_tier           TEXT NOT NULL,          -- tier0_dgca | tier1_google_flights | tier2_airline_direct
    source_detail         TEXT NOT NULL,
    origin                CHAR(3) NOT NULL,
    destination           CHAR(3) NOT NULL,
    departure_date        DATE,                    -- NULL for Tier 0 bands
    booking_window_days   INTEGER,
    airline               TEXT,
    fare_type             TEXT,
    price                 NUMERIC(10, 2),
    currency              TEXT DEFAULT 'INR',
    is_price_band         BOOLEAN DEFAULT FALSE,
    raw_ref               TEXT
);

CREATE INDEX IF NOT EXISTS idx_fare_obs_route_date
    ON fare_observations (origin, destination, departure_date);

CREATE INDEX IF NOT EXISTS idx_fare_obs_observed_at
    ON fare_observations (observed_at_utc);

-- Optional: if TimescaleDB extension is available, turn this into a
-- hypertable for efficient time-range queries (brief §7, "Storage" row).
-- Uncomment if you have the extension installed:
-- CREATE EXTENSION IF NOT EXISTS timescaledb;
-- SELECT create_hypertable('fare_observations', 'observed_at_utc', if_not_exists => TRUE);


-- ============================================================
-- Hackathon prototype additions: Stage 3 (cleaning) and
-- Stage 4 (index) outputs. See docs/DESIGN_hackathon_prototype.md.
-- ============================================================

-- Deliberately NOT "LIKE fare_observations INCLUDING ALL": that would
-- copy the raw table's identity/sequence definition verbatim, which in
-- Postgres makes both tables share one sequence and collide on insert.
-- Defined explicitly instead, with its own id sequence.
CREATE TABLE IF NOT EXISTS fare_observations_clean (
    id                    BIGSERIAL PRIMARY KEY,
    observed_at_utc       TIMESTAMPTZ NOT NULL,
    source_tier           TEXT NOT NULL,
    source_detail         TEXT NOT NULL,
    origin                CHAR(3) NOT NULL,
    destination           CHAR(3) NOT NULL,
    departure_date        DATE,
    booking_window_days   INTEGER,
    airline               TEXT,
    fare_type             TEXT,
    price                 NUMERIC(10, 2),
    currency               TEXT DEFAULT 'INR',
    is_price_band          BOOLEAN DEFAULT FALSE,
    raw_ref                 TEXT,
    is_duplicate            BOOLEAN DEFAULT FALSE,
    is_outlier              BOOLEAN DEFAULT FALSE,
    cleaned_at_utc           TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_fare_obs_clean_route_date
    ON fare_observations_clean (origin, destination, departure_date);

CREATE TABLE IF NOT EXISTS airfare_index (
    id               BIGSERIAL PRIMARY KEY,
    computed_at_utc  TIMESTAMPTZ NOT NULL,
    origin           CHAR(3) NOT NULL,
    destination      CHAR(3) NOT NULL,
    base_period      DATE NOT NULL,
    index_value      NUMERIC(10, 4) NOT NULL,
    n_observations   INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_airfare_index_route
    ON airfare_index (origin, destination, computed_at_utc);
