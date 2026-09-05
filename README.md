# SIH26056 — Airfare Data Acquisition Prototype

Working code for the tiered acquisition pipeline described in
`docs/PRD.md`, `docs/TECH_STACK.md`, and `docs/DESIGN.md`. Read the PRD
first — it explains why MakeMyTrip is deliberately not a target in this
codebase.

## Repo layout
```
config.py                    routes, booking windows, throttling, storage target
storage.py                   shared FareObservation record + persist() -> CSV/Postgres
logging_setup.py             shared rotating-file + console logger
robots_check.py              fail-closed robots.txt gate, used by Tier 2/3

collector_tier1.py           Tier 1: Google Flights via fast-flights (READY TO RUN)
collector_tier0_dgca.py      Tier 0: DGCA tariff PDF downloader + parser (needs URLs filled in)
collector_tier2_airline.py   Tier 2: curl_cffi against one airline's JSON endpoint (needs endpoint filled in)

schema.sql                   optional Postgres/TimescaleDB schema
docs/PRD.md                  what "done" means, legal guardrail, scope
docs/TECH_STACK.md           full stack + what was deliberately deferred
docs/DESIGN.md               architecture, degradation ladder, anti-bot mapping
```

## Phase-by-phase execution

### Phase 1 — today: get Tier 1 running (this is the "do not delay" item)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# sanity check the fast-flights import before trusting the collector
python -c "from fast_flights import FlightData, Passengers, get_flights; print('ok')"

# one manual pass, all 3 routes x 4 booking windows
python collector_tier1.py

# check output
head data/fare_observations.csv

# if that looks right, start the hourly loop on whatever machine stays on
nohup python collector_tier1.py --loop > logs/tier1_stdout.log 2>&1 &
```
If the `fast_flights` import above fails, the library's API has moved —
see the fix instructions in `collector_tier1.py`'s module docstring
before touching anything else.

**Deploying on a free-tier VM (Oracle Always Free / GCP):** SSH in,
repeat the steps above, then either keep the `--loop` process running
under `tmux`/`screen`, or better, set up a systemd service:
```ini
# /etc/systemd/system/sih-tier1.service
[Unit]
Description=SIH26056 Tier 1 collector
After=network.target

[Service]
WorkingDirectory=/home/<you>/sih26056-collector
ExecStart=/home/<you>/sih26056-collector/.venv/bin/python collector_tier1.py --loop
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable --now sih-tier1
```

### Phase 2 — this week: Tier 0 and Tier 2, and the per-source difficulty check
1. **Tier 0**: one person spends ~30 min finding one airline's current
   published tariff-sheet URL (check the airline's fares/investor-relations
   page). Add it to `TARIFF_SOURCES` in `collector_tier0_dgca.py`, then:
   ```bash
   pip install pdfplumber
   python collector_tier0_dgca.py
   ```
   Manually check the first output rows against the PDF by eye — the
   regex extractor is a starting point, not a validated parser (see the
   warning it logs).

2. **Tier 2**: one person opens the chosen airline's flight-search page in
   Chrome DevTools (Network → Fetch/XHR), runs a search, finds the JSON
   response, and fills in `SEARCH_ENDPOINT` and `build_request()` in
   `collector_tier2_airline.py` per that file's docstring. Then:
   ```bash
   pip install curl_cffi
   python collector_tier2_airline.py
   ```
   This always checks `robots.txt` first (`robots_check.py`) and refuses
   to run if the endpoint's path is disallowed — if that happens, pick a
   different airline rather than routing around the check.

3. **Read robots.txt for all 4-5 candidate airline domains by hand**
   (brief's open item #3) and note which paths are off-limits. Keep this
   note in `docs/` so the whole team can see it before writing more Tier
   2/3 code.

### Phase 3 — weeks 5-12: degradation ladder, selective Tier 3
Only after Phase 1-2 are solid. Implement and demo the degradation
behaviour from `docs/DESIGN.md` §4 (kill a `source_tier` in a query, show
the index still computes). Any Tier 3 addition needs an individual
robots.txt check for that exact page — no blanket OTA scraping, and
MakeMyTrip stays excluded per `docs/PRD.md` §7.

## Postgres, if you want it instead of CSV
```bash
createdb airfare
psql airfare -f schema.sql
export DATABASE_URL="postgresql+psycopg2://user:pass@localhost:5432/airfare"
python collector_tier1.py   # now writes to Postgres instead of CSV
```

## Phase 4 — internal hackathon: Stages 3–6 (cleaning, index, anomaly, dashboard, API)
See `docs/PRD_hackathon_prototype.md`, `docs/TECH_STACK_hackathon_prototype.md`,
`docs/DESIGN_hackathon_prototype.md` for the full design. These stages
**require Postgres** — CSV-only mode (fine for Stage 1/2) doesn't support
the cross-observation SQL these need.

```bash
export DATABASE_URL="postgresql+psycopg2://user:pass@localhost:5432/airfare"
psql "$DATABASE_URL" -f schema.sql        # creates the new tables too

pip install -r requirements.txt            # now includes pandas, streamlit, fastapi, etc.

# after Tier 1/2 collectors have written some rows to fare_observations:
python cleaning.py                          # Stage 3: dedup + outlier flags -> fare_observations_clean
python index_calc.py                         # Stage 4: route-level Laspeyres-style index -> airfare_index
python anomaly.py                             # Stage 5: scan for anomalies, logs ALERT lines
python anomaly.py --inject-test-anomaly        # Stage 5 demo: prove the detector works, no real data touched

streamlit run dashboard.py                      # Stage 6: dashboard at http://localhost:8501
uvicorn api:app --reload --port 8000              # Stage 6: API, try http://localhost:8000/docs
```

**Suggested demo order for the internal hackathon:** run the collectors
for at least a day beforehand so `fare_observations` has real spread ->
run cleaning + index_calc live in the demo (fast, a few seconds) -> show
`anomaly.py --inject-test-anomaly` catching the synthetic spike live ->
open the dashboard and the API `/docs` page side by side.

**VS Code / Antigravity IDE:** no special config needed for either.
Open the folder, point the interpreter at `.venv`, run any script with
the built-in Python runner or the integrated terminal. Nothing here is
notebook-based or IDE-specific.

## What I could not verify from here
I don't have live network access from this sandbox to actually run
`fast-flights` against Google, or to inspect a real airline's DevTools
Network tab. Everything above is syntax-checked and logically complete,
but the **first real run on your machine is the actual test** — budget
the "one evening" the brief mentions for exactly that first run, not just
for writing the code.
