# Project Notes — Urban Mobility Explorer

Running notes for the technical report. Update this as each team member completes their work.

---

## Team Roles

| Member | Role | Folder |
|--------|------|--------|
| Nshimyumurwa Mary Therese | Team Lead, Flask API, Database Design | `backend/` |
| Clive Mushipe | Data Pipeline, Backend Support | `backend/`, `database/` |
| Davy Dushimiyimana | Frontend Dashboard | `frontend/` |
| Aimable Bancunguye | DSA Implementation | `dsa/` |
| Eloi Mizero | Documentation and Technical Report | `docs/` |

---

## Day 1 — Report Structure Setup

- Created `docs/report.pdf` with all five required sections.
- Content is grounded in the current codebase (Flask API, SQLite schema, insertion sort, dashboard).
- Placeholders marked with `[TBD — Name]` for sections teammates will expand.

### What's in the repo today

- **Backend (`app.py`)**: REST API on port 5000 with endpoints for trips, summaries (by borough, hour, time-of-day, zone), zones, exclusions, and health check. Supports pagination and rich filtering.
- **Database (`schema.sql`)**: Three tables — `zones`, `trips`, `exclusion_log`.
- **Data pipeline (`data_pipeline.py`)**: Loads NYC TLC parquet data, cleans outliers, derives `trip_duration_minutes`, `fare_per_mile`, `speed_mph`.
- **DSA (`algorithm.py`)**: Custom insertion sort to rank trips by fare without built-in sort functions.
- **Frontend (`index.html`)**: Dashboard with KPI meters, Chart.js visualizations, filters, trip explorer table, exclusion log view.

### Content still needed from teammates

- [ ] **Therese / Clive** — Final data pipeline stats (rows loaded, exclusion counts, cleaning rationale details)
- [ ] **Davy** — Dashboard UX decisions, chart choices, filter behaviour
- [ ] **Aimable** — Benchmark results, why insertion sort was chosen, integration with API (if any)
- [ ] **All** — Final insights once real dataset is loaded and analysed

---

## Insights Log

_Add dated entries as findings emerge from the dashboard and analysis._

| Date | Finding | Source |
|------|---------|--------|
| — | Manhattan is the origin of over 90% of recorded trips (per README) | README / pending verification |
| — | Late-night fares (midnight–3am) tend to be higher than daytime | README / pending verification |
| — | Average speed drops during morning rush (7–9am) | README / pending verification |

---

## Report Build

```bash
cd docs
python3 -m venv .venv          # first time only
source .venv/bin/activate
pip install fpdf2
python generate_report.py
```

Output: `docs/report.pdf`
