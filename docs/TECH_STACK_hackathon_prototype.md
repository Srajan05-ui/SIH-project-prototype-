# Tech Stack — AirPrice India: Internal Hackathon Prototype

Builds on `docs/TECH_STACK.md` (acquisition layer, Stages 1–2). This
covers Stages 3–6 and the dev environment.

## Dev environment
| Tool | Use |
|---|---|
| VS Code | Primary editor. `requirements.txt` + a `.venv` is all it needs — no special config beyond a Python interpreter select. |
| Antigravity IDE | Works the same way as VS Code here — this is a plain Python project with no IDE-specific config, no notebooks, no proprietary project files. Open the folder, select/create the `.venv` interpreter, run scripts normally. Nothing in this repo is IDE-locked. |
| `.venv` + `requirements.txt` | Single dependency source of truth (updated list below). No Docker needed for the hackathon scope — one Postgres instance and Python scripts. |

## Stage 1–2 (unchanged, already built)
fast-flights, curl_cffi, PostgreSQL+TimescaleDB, tenacity, robots.txt gate.
See `docs/TECH_STACK.md`.

## Stage 3 — Cleaning & normalisation
| Component | Choice | Why |
|---|---|---|
| Dedup / outlier logic | `pandas` (IQR-based flagging) | No new dependency; the whole team already knows pandas; IQR outlier detection is explainable in 30 seconds to a judge — important, since "how does this work" is a judged question. |
| Currency/unit normalisation | Plain Python in `cleaning.py` | All sources already emit INR; the real normalisation work is fare-type harmonisation (`published_band` vs transacted price), which is a business-logic decision, not a library problem. |

## Stage 4 — Index computation
| Component | Choice | Why |
|---|---|---|
| Index formula | Hand-written Laspeyres-style calc in `index_calc.py` | A fixed-basket Laspeyres index is a weighted-average ratio — no library adds value over 20 lines of pandas. Writing it by hand also means the team can explain every line, which matters more than using a stats package for something this simple. |
| Base period | First day of collected data (documented, not hardcoded to a real CPI base period — the prototype's base period is "when we started collecting," and the deck should say so). | Honesty > looking more mature than the data supports. |

## Stage 5 — Anomaly detection
| Component | Choice | Why |
|---|---|---|
| Default (hackathon-scope) | Rolling z-score / IQR band on `pandas` | Works meaningfully on days of data. Isolation Forest and Prophet (your image's suggestion) both want weeks-to-months of history to avoid flagging noise as anomalies — with 2-3 days of hackathon data they'd likely just fire constantly or never. |
| Optional upgrade path | `scikit-learn` `IsolationForest` | Wired in as a swappable strategy in `anomaly.py` (`METHOD = "zscore"` vs `"isolation_forest"`), not removed from the plan — just not the default, and the code says why. |
| Alerting | Python `logging` (console + file) | A real email/Slack integration is a half-day of OAuth/webhook setup that doesn't change what's being demoed. Logging the alert with a clear "ALERT:" prefix is enough to show the mechanism; wire up Slack post-hackathon if useful. |

## Stage 6 — Dashboard & API
| Component | Choice | Why |
|---|---|---|
| Dashboard | **Streamlit**, not Grafana | Grafana needs its own server, data-source config, and provisioning — real setup time for a hackathon. Streamlit is `pip install streamlit`, one Python file, `streamlit run dashboard.py`, done. Matches your image's "Streamlit or Grafana" option; Streamlit is the faster path to a demoable UI. |
| API | **FastAPI**, minimal | One endpoint (`GET /index/latest`) returning JSON, auto-generated docs at `/docs` for free (nice in a demo — a judge can hit "Try it out" themselves). No auth layer for the hackathon; the PRD flags this as a documented non-goal, not an oversight. |
| Chart library (inside Streamlit) | `plotly` via `st.plotly_chart`, or `st.line_chart` for the simplest case | `st.line_chart` needs zero extra code for a first pass; swap to plotly only if you want hover tooltips/zoom for the demo. |

## Updated `requirements.txt` additions for Stages 3–6
```
pandas>=2.0          # already present (Stage 1), reused for 3-5
scikit-learn>=1.4     # optional, Stage 5 IsolationForest path only
streamlit>=1.35        # Stage 6 dashboard
fastapi>=0.111          # Stage 6 API
uvicorn>=0.29            # Stage 6 API server
plotly>=5.20              # optional, nicer dashboard charts
```

## What's explicitly NOT in the hackathon stack
- Grafana, Kafka/Redpanda, Docker, Kubernetes, any cloud-managed DB —
  all reasonable for the production system (see the acquisition
  `DESIGN.md` §6 "Production path"), all unnecessary weight for a
  prototype that needs to run on one laptop before a demo slot.
- Prophet / Isolation Forest as the *default* anomaly method — available
  as an upgrade path, not required to get the demo working.
