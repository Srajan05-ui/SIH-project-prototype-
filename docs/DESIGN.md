# Design Doc — SIH26056 Airfare Data Acquisition

## 1. Architecture (Phase 1–2 scope, this repo)

```
                    ┌─────────────────────┐
                    │   config.py          │  routes, windows, throttling,
                    │                       │  storage target (CSV/PG)
                    └─────────┬────────────┘
                              │
     ┌────────────────────────┼────────────────────────┐
     │                        │                          │
┌────▼─────┐          ┌───────▼────────┐         ┌───────▼────────┐
│ Tier 0    │          │ Tier 1          │         │ Tier 2          │
│ DGCA PDFs │          │ Google Flights  │         │ Airline JSON     │
│ pdfplumber│          │ fast-flights    │         │ curl_cffi        │
│ monthly   │          │ hourly          │         │ hourly, gated by │
│           │          │                 │         │ robots_check.py  │
└────┬─────┘          └───────┬────────┘         └───────┬────────┘
     │                        │                          │
     └────────────┬───────────┴──────────────┬───────────┘
                   │                          │
             ┌─────▼──────────────────────────▼─────┐
             │   storage.py :: FareObservation        │
             │   persist()  -> CSV (default)          │
             │               -> Postgres (if DATABASE_URL) │
             └─────────────────────────────────────────┘
```

Every tier produces the same `FareObservation` record shape (see
`storage.py` docstring). This is the load-bearing design decision: an
index calculator built downstream never needs to know which tier a row
came from except as a quality flag (`source_tier`, `is_price_band`).

## 2. Why one record shape, not one table per tier
The brief's degradation ladder (§6.3) only works if losing Tier 3 (or
Tier 2) is a `WHERE source_tier != 'x'` filter, not a schema migration.
A single flat table/CSV makes "compute the index from whatever tiers are
currently healthy" a query, not an engineering project.

## 3. Anti-bot posture, mapped to what's actually implemented here
| Brief's control (§3) | Where it lives in this repo |
|---|---|
| Throttling, jitter, per-domain concurrency cap | `config.MIN_DELAY_SECONDS`/`MAX_DELAY_SECONDS`, applied in every collector's `finally:` block |
| Exponential backoff, stop after N failures per cycle | `tenacity` retry decorator in `collector_tier1.py` / `collector_tier2_airline.py`; failures are logged and the cell is dropped for that cycle, not retried into a ban |
| Honour robots.txt | `robots_check.py`, called before every Tier 2 request; fails **closed** (treats an unreadable robots.txt as disallow) |
| Identify ourselves | `config.PROJECT_USER_AGENT_NOTE`, included in Tier 0 request headers; Tier 2 template has a slot for it |
| CAPTCHA: avoid, never solve | No CAPTCHA-handling code exists anywhere in this repo. A 403/429 is treated as a stop signal (see `_fetch` in Tier 2), not a puzzle to solve |
| Store observations, not pages | `storage.py`'s schema has no raw-HTML/PDF column; `raw_ref` is a pointer/filename, not the payload itself |

## 4. Degradation ladder (implemented as a query pattern, not new code)
Since every tier writes to the same table:
- **One source dies:** downstream index query filters `WHERE source_tier
  IN (...)` to the tiers still healthy. No code change.
- **Multiple tiers die:** fall back to `source_tier = 'tier0_dgca'`
  (`is_price_band = TRUE`) plus any manual validation rows, and the
  index publisher documents the reduced basis — exactly brief §6.3's
  table, expressed as a filter instead of a failover mechanism.

## 5. Legal design decisions baked into the code (not just the PRD)
- `robots_check.py` is **fail-closed**: if robots.txt can't be fetched or
  parsed, the request is treated as disallowed, not allowed. This is a
  deliberate bias toward the safer failure mode.
- MakeMyTrip is not referenced anywhere in the codebase as a target. This
  isn't an oversight — its robots.txt disallows automated access and the
  team's own legal research (OLX v. Padawan) makes it the wrong first
  target for a MoSPI-facing prototype. See PRD §7.
- `storage.py` never persists raw HTML or PDF bytes into the shared
  table — only structured fields plus a filename/id pointer — to keep the
  compilation-copyright exposure the brief flags (§5.1, Eastern Book Co.)
  as small as the design can make it.

## 6. Production path (what changes if MoSPI actually runs this)
Not built here, but the design doesn't block it:
- Tier 0 becomes a direct DGCA monthly filing feed rather than PDF
  scraping, per the brief's "partnership route" (§6.2).
- Tier 2 becomes a small number of negotiated airline data-sharing
  agreements instead of reverse-engineered endpoints.
- Tier 3 either stays dropped or becomes a paid, ToS-compliant data feed
  — the brief's Phase 3 costed line item, not something absorbed for
  free.
- `storage.py`'s Postgres path already points at where an append-only
  event log (Kafka/Redpanda per brief §7) would sit in front of it, if
  reproducibility auditing becomes a hard requirement.

## 7. What is deliberately NOT in this repo yet
- Scrapy orchestration — not needed at 1 airline / 3 routes; add when
  Tier 2 grows past ~3 airlines.
- Playwright/Patchright browser tier — no current source in this repo
  needs JS rendering. Add only when a specific Tier 2 endpoint proves it
  requires one, per brief §2.2's rule: "do not launch a browser unless
  the page genuinely requires one."
- Any OTA integration — see PRD §5, Tier 3 row.
