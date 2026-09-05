# PRD — AirPrice India: Internal Hackathon Prototype (SIH26056)

## 1. What this document covers
The SIH-facing PRD (`docs/PRD.md` in the acquisition repo) scoped Phase 1
acquisition only. This PRD scopes the **internal hackathon prototype**:
a complete, working, end-to-end slice of the full 6-stage pipeline your
team designed (ingestion → storage → cleaning → index → anomaly →
dashboard), demoed on real data.

## 2. Why a vertical slice, not a deep single stage
Judges at an internal hackathon score "does this actually work" higher
than "how sophisticated is one component." A pipeline that produces one
real, defensible index number from real fares, visible on a dashboard,
beats a scraper that pulls 10 sources into a table nobody queries. Scope
is deliberately narrow so every stage is real, not mocked:

- **3 routes**: DEL–BOM, BOM–BLR, DEL–BLR (same as the acquisition repo)
- **2 sources**: Tier 1 (Google Flights / fast-flights) + Tier 2 (one
  airline direct JSON endpoint via curl_cffi). No OTA source in this
  prototype — see §7 for why, unchanged from the acquisition PRD.
- **3 booking windows**: 7, 15, 30 days ahead
- **Economy, one-way only**

## 3. Stage-by-stage scope for the hackathon build

| Stage | Full production vision (your image) | Hackathon prototype scope |
|---|---|---|
| 1. Ingestion | Playwright/Selenium + BeautifulSoup/Scrapy across OTAs, 2–3x/day, proxy rotation | **Reused as-is**: `collector_tier1.py` (fast-flights) + `collector_tier2_airline.py` (curl_cffi), hourly, no proxies. See §7 for the OTA/Selenium/proxy delta. |
| 2. Raw storage | PostgreSQL time-series, full audit trail | PostgreSQL (schema already built: `schema.sql`). Timestamped, source-tagged, route-tagged — already the `FareObservation` shape. |
| 3. Cleaning & normalisation | Dedup, outlier removal, base fare + taxes in INR, economy one-way, interpolation | `cleaning.py` (new): dedup on `(source_tier, origin, destination, departure_date, airline, observed hour)`; IQR-based outlier flagging; missing-cell interpolation is a documented stub, not faked data. |
| 4. Index computation | Laspeyres-style, route/category/national, seasonal adjustment | `index_calc.py` (new): fixed-basket Laspeyres at route level for the 3 routes; category/national rollup and seasonal adjustment are **out of scope** for the hackathon (need >1 month of data to mean anything) — documented as a stretch goal, not silently skipped. |
| 5. Anomaly detection | Isolation Forest / Prophet, automated alert to data managers | `anomaly.py` (new): rolling z-score / IQR-based flagging is the hackathon-scope method (works on days of data; Isolation Forest/Prophet need more history than a hackathon collects). Isolation Forest is wired in as an **optional upgrade path**, not the default, and documented as such. Alerts print/log; no real email/Slack integration for the demo. |
| 6. Dashboard + API | Streamlit/Grafana + secure REST API for CPI pipeline integration | `dashboard.py` (Streamlit, new). A minimal FastAPI (`api.py`, new) exposes the latest index values as JSON — enough to demo "automated integration," not a production auth-hardened API. |

## 4. Success criteria for the internal demo
1. Live (or very recently run) data exists in Postgres for at least 3
   routes across at least 2 source tiers.
2. `index_calc.py` produces a real Laspeyres-style number per route that
   the team can explain and defend if asked "how did you compute this."
3. `anomaly.py` correctly flags at least one deliberately-injected price
   spike in a test run (this is your proof point — see Design doc §5).
4. `dashboard.py` shows route-wise fare trends and the computed index,
   reading live from Postgres.
5. `api.py` returns the current index as JSON from a single `curl` or
   browser hit — the "automated integration" story in one command.

## 5. Non-goals for this prototype
- OTA scraping (MakeMyTrip et al.) — unchanged decision from the
  acquisition PRD, see §7.
- Proxy rotation — no source in scope needs it (Tier 1/2 only).
- Production-grade auth on the API — a demo endpoint, not a deployed one.
- Seasonal adjustment and national-level index — need more history than a
  hackathon timeframe provides; documented as Phase 2, not silently cut.

## 6. What changed vs. the acquisition-only PRD
The acquisition PRD (Tier 0/1/2/3, legal guardrails) is unchanged and
still governs ingestion. This PRD adds Stages 3–6 on top of it. Nothing
here relaxes the robots.txt / no-CAPTCHA / no-MakeMyTrip decisions —
they're inherited, not re-litigated.

## 7. Reconciling the image's Stage 1 with the acquisition plan
Your Stage-1 slide describes Playwright/Selenium against JS-heavy OTA
sites, 2–3 runs/day, with proxy rotation and anti-bot handling as
first-class. That's a reasonable **production-scale** design, but for
this prototype:
- **Selenium** → not used; your own brief says avoid it for new code, and
  the acquisition repo already standardised on Playwright as the browser
  fallback (unused so far — Tier 1/2 haven't needed it).
- **Proxy rotation** → not used; nothing in the 2-source hackathon scope
  needs it, and free proxies are documented as unreliable/risky.
- **OTA sites** → not used; MakeMyTrip's `robots.txt` disallows automated
  access site-wide (verified during the acquisition build), and it's the
  fact pattern the OLX v. Padawan precedent lost on. If the team wants an
  OTA in a *future* iteration, it needs a specific page whose own
  robots.txt clears it — not a blanket "OTA sites" target.

This isn't scaling back ambition — it's building the parts of Stage 1 the
team can actually defend live if a judge asks "did you check robots.txt
for that."
