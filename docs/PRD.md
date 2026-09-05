# PRD — Airfare Data Acquisition Prototype (SIH26056)

## 1. Problem
MoSPI needs real-time-ish domestic airfare data to feed a CPI-grade airfare
index. There is no free, unlimited, real-time airfare API (Amadeus
Self-Service shut down 17 Jul 2026; no public Google Flights API exists).
Direct scraping of the sources that do exist has a genuine anti-bot and
legal-exposure problem. This project acquires the data; index methodology
and dashboarding are separate workstreams (out of scope here).

## 2. Goal for this prototype (SIH submission)
Demonstrate a **working, tiered acquisition pipeline** that:
1. Produces real fare observations for a handful of Indian domestic routes,
   collected over several days before the presentation.
2. Degrades gracefully — losing one source narrows coverage, never breaks
   the system.
3. Stays inside a defensible legal position: no CAPTCHA solving, no
   evasion of an explicit access restriction, robots.txt honoured per
   domain, no institutional network used against a defended target.

## 3. Non-goals (explicitly out of scope for this prototype)
- Index calculation / CPI methodology.
- A production-grade OTA scraper. OTAs (Tier 3) are enrichment only, and
  only where a specific page's robots.txt permits it — see §5.
- Any CAPTCHA-solving integration.
- Real-time (sub-hourly) collection. Hourly is the target cadence.

## 4. Users
- **Internal (this team):** needs a running collector before the demo and
  a clean CSV/Postgres table to build an index prototype on top of.
- **Judging panel:** needs to see (a) real data accumulating, (b) an
  honest account of what's hard and why, (c) a degradation story.
- **MoSPI (aspirational, post-hackathon):** the production version of this
  system would sit inside MoSPI's data pipeline; the prototype should make
  that path visible (see design doc, §"Production path").

## 5. Source tiers and what "done" looks like per tier

| Tier | Source | Definition of done for the prototype |
|---|---|---|
| 0 | DGCA-mandated tariff PDFs | At least one airline's PDF downloaded and parsed into fare-band rows; team has manually verified a sample against the PDF by eye. |
| 1 | Google Flights via `fast-flights` | Hourly collector running unattended on 3 routes x 4 booking windows, writing to CSV/Postgres, for at least 48h before the demo. |
| 2 | One airline's direct JSON endpoint via `curl_cffi` | Endpoint identified via DevTools, robots.txt-checked, at least one successful pull with real fares for at least one route. |
| 3 | OTA (optional, only if a *specific page's* robots.txt allows it) | Not required for the demo. If pursued: single page, low volume, no login, no CAPTCHA interaction, and only after a per-domain robots.txt check passes. **MakeMyTrip is explicitly excluded** — its robots.txt disallows automated access site-wide; see legal note below. |

## 6. Success metrics for the SIH demo
- Number of days of continuous Tier 1 data at demo time (target: 3+ days).
- Number of tiers with at least one real, verified observation (target: 3
  of the 4, i.e. Tier 0, 1, 2 minimum).
- A live or recorded demonstration of the degradation ladder: kill one
  source, show the index/collector still produces output with a
  documented coverage caveat.
- Zero CAPTCHA-solving code, zero disallowed-path requests, in the
  codebase — this is a claim the team should be able to defend live if a
  judge asks to see the robots.txt handling.

## 7. Legal guardrail (binding on this prototype, not just a suggestion)
Per the team's own legal research: IT Act s.43 exposure turns substantially
on whether a stated access restriction was respected. MakeMyTrip's
`robots.txt` disallows automated access; OLX v. Padawan (Del HC, 2016) is
a directly analogous precedent where a scraper lost. **This prototype does
not scrape MakeMyTrip or any source whose robots.txt disallows the path
in question.** Tier 2 (airline direct) is the "scrape a real page" story
for the demo instead — lower legal exposure, matches the team's own
curl_cffi pipeline design, and is what the source-tier table above already
recommends contributing the most statistical value per unit of risk.

## 8. Open items carried over from the brief (§8)
Unchanged — still needs a team decision: which machine runs Phase 1 24/7,
final route/booking-window list for the index (not just the acquisition
demo), and who's checking each target's robots.txt by hand before Tier 2/3
code goes further than templates.
