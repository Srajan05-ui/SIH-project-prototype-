# Design Doc — AirPrice India: Internal Hackathon Prototype

Extends `docs/DESIGN.md` (Stages 1–2, already built). This covers the
new Stage 3–6 modules and how the whole 6-stage pipeline fits together.

## 1. Full pipeline, as actually implemented

```
┌───────────────┐   ┌───────────────┐
│ collector_tier1│   │ collector_tier2│         Stage 1 (existing)
│ (fast-flights) │   │ (curl_cffi)    │
└───────┬───────┘   └───────┬───────┘
        │                    │
        └─────────┬──────────┘
                   ▼
          storage.py :: persist()                Stage 2 (existing)
                   ▼
         PostgreSQL: fare_observations
                   │
                   ▼
            cleaning.py                          Stage 3 (new)
     dedup → outlier flag → normalise
                   ▼
      PostgreSQL: fare_observations_clean
                   ▼
            index_calc.py                        Stage 4 (new)
     Laspeyres-style, per route, per run
                   ▼
       PostgreSQL: airfare_index
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
   anomaly.py             dashboard.py            Stage 5 / 6 (new)
   (flags + logs)         (Streamlit, reads
                            fare_observations_clean
                            + airfare_index)
                                │
                                ▼
                            api.py
                       (FastAPI, GET /index/latest)
```

## 2. New tables (additions to `schema.sql`)

```sql
-- Stage 3 output: same shape as fare_observations, plus cleaning flags
CREATE TABLE IF NOT EXISTS fare_observations_clean (
    LIKE fare_observations INCLUDING ALL,
    is_duplicate   BOOLEAN DEFAULT FALSE,
    is_outlier     BOOLEAN DEFAULT FALSE,
    cleaned_at_utc TIMESTAMPTZ
);

-- Stage 4 output: one row per route per computation run
CREATE TABLE IF NOT EXISTS airfare_index (
    id               BIGSERIAL PRIMARY KEY,
    computed_at_utc  TIMESTAMPTZ NOT NULL,
    origin           CHAR(3) NOT NULL,
    destination      CHAR(3) NOT NULL,
    base_period      DATE NOT NULL,
    index_value      NUMERIC(10, 4) NOT NULL,   -- 100 = base period
    n_observations   INTEGER NOT NULL
);
```
(Full statements added to `schema.sql` alongside the existing table —
see the file itself.)

## 3. Stage 3 — `cleaning.py` design
- **Dedup key**: `(source_tier, origin, destination, departure_date,
  airline, date_trunc('hour', observed_at_utc))` — two observations from
  the same source within the same hour for the same route/date/airline
  are the same underlying scrape event, not two data points.
- **Outlier flag, not outlier deletion**: rows outside
  `[Q1 - 1.5*IQR, Q3 + 1.5*IQR]` per `(origin, destination,
  departure_date)` group are flagged `is_outlier = TRUE`, never dropped.
  Index computation excludes flagged rows by default but they stay
  queryable — deleting data your index didn't use is how you lose the
  ability to explain a judge's "why is this fare missing" question.
- **Missing-cell interpolation**: documented as a **stub that raises
  `NotImplementedError`** with a comment explaining why (needs a real
  missing-data policy — carry-forward vs linear interpolation vs drop —
  which is a methodology decision the PRD explicitly defers, not
  something to silently guess at in code).

## 4. Stage 4 — `index_calc.py` design
Laspeyres-style, fixed-basket, single "item" (the route itself) per
computation:

```
index_value(route, t) = 100 * (price(route, t) / price(route, base_period))
```

- **Base period**: the earliest cleaned observation per route (documented
  in the output row as `base_period`, never hidden).
- **`price(route, t)`**: mean of non-outlier, non-duplicate observations
  for that route within the current run's collection window.
- **Category/national rollup**: explicitly out of scope (PRD §3) —
  `index_calc.py` only computes route-level, and says so in its
  docstring, rather than fabricating a weighted national number from 3
  routes that wouldn't be statistically meaningful anyway.

## 5. Stage 5 — `anomaly.py` design and the demo proof point
Default method: rolling z-score over the last N observations per route
(`N` configurable, default 10). A row where
`abs(price - rolling_mean) > 2.5 * rolling_std` is flagged and logged as
`ALERT: possible anomaly ...`.

**How to actually demo this working** (since real fares may not spike
during your demo window): the script accepts a `--inject-test-anomaly`
flag that adds one synthetic high-price row to a copy of the data in
memory only (never written to the real table) and shows the detector
catching it. This is the honest way to prove the mechanism works without
either waiting for a real spike or quietly faking real-looking data in
the actual dataset.

## 6. Stage 6 — `dashboard.py` and `api.py`
- `dashboard.py` (Streamlit): reads `fare_observations_clean` and
  `airfare_index` directly from Postgres on each page load (no caching
  layer needed at hackathon data volumes). Three panels: route-wise fare
  trend line chart, current index value per route, a table of the most
  recent anomaly flags.
- `api.py` (FastAPI): single `GET /index/latest` returning the most
  recent `airfare_index` row per route as JSON. This is the whole
  "automated integration into the CPI pipeline" story made concrete
  enough to demo with one `curl` command or the auto-generated `/docs`
  page.

## 7. What "done" looks like structurally
Every stage reads from and writes to Postgres — no stage passes data to
the next one in-memory or via a file. This is deliberate: a judge (or a
teammate) can inspect the state of the pipeline at any stage with a
plain SQL query, which is a much stronger "is this real" signal than a
script that only prints to stdout.
