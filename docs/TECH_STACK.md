# Tech Stack — SIH26056 Airfare Data Acquisition

| Layer | Choice | Why (and what we deliberately did NOT pick) |
|---|---|---|
| Language | Python 3.11+ | Every library needed (fast-flights, curl_cffi, pdfplumber, Scrapy) is Python-first. |
| Tier 1 HTTP | `fast-flights` (protobuf query to Google Flights) | No API key, no browser. This is the highest value-per-hour item in the whole project — see PRD §6. |
| Tier 2 HTTP | `curl_cffi` (Chrome TLS/HTTP2 impersonation) | Matches the airline's own JSON endpoint without a browser; far lighter and less detectable than Selenium/Playwright for endpoints that don't need JS execution. |
| Tier 0 parsing | `pdfplumber` | Simple, dependency-light PDF text/table extraction for tariff sheets. |
| Browser automation (held in reserve) | Playwright + Patchright | Only for pages that genuinely require rendering — not used in the Phase 1/2 code in this repo. Patchright is a drop-in over Playwright if we need it later. |
| Orchestration scraping framework (held in reserve) | Scrapy | For when we have enough Tier 2 sources that request scheduling/dedup/pipelines earn their keep. Not needed for 1 airline + 3 routes. |
| HTML parsing (held in reserve) | BeautifulSoup | For any read-only, robots.txt-permitted HTML page (e.g. a public fare-comparison page) if we add one. Not used against MakeMyTrip — see PRD §7. |
| Retry/backoff | `tenacity` | Exponential backoff with jitter on 429/403, per brief §3.2. |
| Storage (default) | CSV (`storage.py`, `persist()`) | Zero setup, works from minute one. |
| Storage (optional) | PostgreSQL (+ TimescaleDB if available) | Switches on automatically if `DATABASE_URL` is set — see `config.py`. Schema in `schema.sql`. |
| Scheduling | Python `--loop` mode now; `cron` or `systemd timer` on the VM later | Simplicity first; brief's APScheduler suggestion is a fine upgrade once Scrapy orchestration is added. |
| Hosting | Any always-on machine (Oracle Always Free / GCP free-tier VM / a laptop that stays on) | Zero cost per brief §4.2 Phase 1. |
| Proxies | None | Tiers 0-2 as scoped don't need them. Revisit only if a specific Tier 2/3 source proves it requires one (brief §4.2 Phase 2/3). |

## Explicitly deferred (not because they're wrong, because they're not needed yet)
- **Apify**: useful if we later want managed, scheduled Actor runs instead
  of a self-hosted VM loop. Reasonable Phase 3 swap for the orchestration
  layer, not needed while the whole system is 1 VM + cron.
- **Selenium**: no code path in this repo uses it. If a future Tier 2/3
  source turns out to require full JS rendering, add Playwright first
  (brief §2.1 — Selenium is "avoid for new code").
- **CAPTCHA solvers**: never. See brief §3.4 and PRD §7 — this is a
  standing decision, not a TODO.

## What "curl_cffi → JSON → Fare" actually looks like in this repo
`collector_tier2_airline.py` implements exactly this pipeline. It ships
with the endpoint URL blank on purpose (see that file's docstring for why
and how to find the real one), so the team makes a deliberate, informed
choice about which airline endpoint to hit rather than the code guessing.
