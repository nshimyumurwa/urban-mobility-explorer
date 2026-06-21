#!/usr/bin/env python3
"""
Generate docs/report.pdf from the structured content in this script.
Run from the docs/ directory after installing fpdf2:

    python3 -m venv .venv && source .venv/bin/activate
    pip install fpdf2
    python generate_report.py
"""

from pathlib import Path

from fpdf import FPDF

OUTPUT = Path(__file__).parent / "report.pdf"

# ---------------------------------------------------------------------------
# Report content — update sections here as teammates provide material.
# Placeholders use [TBD — Name] so it is clear what is still pending.
# ---------------------------------------------------------------------------

TITLE = "Urban Mobility Data Explorer"
SUBTITLE = "Technical Report - Team 2 | ALU Enterprise Web Development"
DATE = "June 2025"

TEAM = [
    ("Nshimyumurwa Mary Therese", "Team Lead, Flask API, Database Design"),
    ("Clive Mushipe", "Data Pipeline, Backend Support"),
    ("Davy Dushimiyimana", "Frontend Dashboard"),
    ("Aimable Bancunguye", "DSA Implementation"),
    ("Eloi Mizero", "Documentation and Technical Report"),
]

SECTIONS = [
    {
        "title": "1. Problem Framing",
        "body": (
            "NYC yellow taxi trips produce millions of records annually. Raw TLC logs include "
            "pickup/dropoff times, fares, distances, and zone IDs, but are hard to interpret "
            "without cleaning, enrichment, and a usable interface.\n\n"
            "We built the Urban Mobility Data Explorer: a full-stack app that processes NYC TLC "
            "yellow taxi data, stores it in SQLite, and serves it via a REST API to an interactive "
            "dashboard. Users filter trips by borough, time of day, fare, and distance; view KPIs; "
            "and inspect individual records.\n\n"
            "Data: yellow_tripdata parquet files, taxi_zone_lookup.csv, taxi_zones spatial metadata "
            "(https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page).\n\n"
            "Key questions: Which boroughs/zones drive demand? How do fares, duration, and speed "
            "vary by time of day? What data quality issues exist and how are exclusions logged?\n\n"
            "[TBD - Team] Final scope once January 2019 data is fully loaded."
        ),
    },
    {
        "title": "2. System Architecture",
        "body": (
            "Three-tier design: data layer, API layer, presentation layer.\n\n"
            "Data flow: TLC parquet -> data_pipeline.py (clean + derive) -> SQLite (mobility.db) "
            "-> Flask REST API -> Chart.js dashboard in the browser.\n\n"
            "Data layer (Clive / database/): schema.sql defines zones (265 NYC zones), trips "
            "(cleaned records + derived features), and exclusion_log (audit trail). "
            "data_pipeline.py loads parquet from data/, cleans outliers, derives "
            "trip_duration_minutes, fare_per_mile, and speed_mph, then writes to mobility.db. "
            "Cleaning removes nulls, duplicates, fares outside $0-$500, distances over 100 mi, "
            "invalid passenger counts, and trips where dropoff precedes pickup or duration exceeds 6 h.\n\n"
            "API layer (Therese / backend/): Flask app (app.py) on port 5000 with CORS. Endpoints "
            "include /api/summary, /api/trips (paginated filters), /api/summary/by-borough, "
            "/api/summary/by-hour, /api/zones, /api/exclusions, and /api/health. db.py handles "
            "SQLite; seed.py provides synthetic fallback data.\n\n"
            "Presentation layer (Davy / frontend/): Chart.js dashboard with KPI meters, demand "
            "charts, borough revenue, time-of-day breakdown, zone rankings, traffic efficiency "
            "scatter (speed vs fare/mile), exclusion log, and paginated trip explorer. "
            "Filters support borough, time-of-day, date range, passenger count, fare and distance "
            "bounds. Trip table supports column sorting and row-level detail modal.\n\n"
            "[TBD - Davy] JS module details. [TBD - Therese] Additional API decisions."
        ),
    },
    {
        "title": "3. Algorithm Explanation",
        "body": (
            "Custom DSA: Insertion Sort (Aimable / dsa/algorithm.py)\n\n"
            "Problem: Rank trips by fare to find the most/least expensive across boroughs without "
            "using sort() or sorted().\n\n"
            "How it works: For each index i, hold the current trip and shift larger-fare neighbours "
            "right until the correct position is found, then insert. Operates in-place on a list of "
            "trip dicts keyed by fare_amount.\n\n"
            "Pseudo-code: for i in 1..n-1: j = i-1; while j >= 0 and trips[j].fare > current.fare: "
            "shift right; insert current at j+1.\n\n"
            "Complexity: Time O(n) best, O(n^2) average/worst. Space O(1).\n\n"
            "Exports: insertion_sort_by_fare(), get_top_expensive_trips(n), get_cheapest_trips(n), "
            "benchmark(). Fetches up to 500 DB rows (no SQL ORDER BY) and sorts in Python.\n\n"
            "[TBD - Aimable] Benchmark results, algorithm choice rationale, API integration plans."
        ),
    },
    {
        "title": "4. Insights",
        "body": (
            "Preliminary findings (README; pending full-dataset verification):\n"
            "  - Manhattan origin for 90%+ of trips (CBD concentration).\n"
            "  - Higher avg fares midnight-3am vs daytime.\n"
            "  - speed_mph drops during morning rush (7-9am).\n\n"
            "Dashboard charts surface these: hourly demand, revenue by borough, time-of-day split, "
            "traffic efficiency scatter, borough rankings.\n\n"
            "[TBD - All] Exact numbers and chart screenshots. "
            "[TBD - Clive] Exclusion log totals and top removal reasons."
        ),
    },
    {
        "title": "5. Reflection",
        "body": (
            "Therese: [TBD] API design, pagination, query performance on large trip tables.\n"
            "Clive: [TBD] Cleaning threshold trade-offs ($500 fare cap, 100 mi distance cap) "
            "and exclusion_log transparency.\n"
            "Davy: [TBD] Filter UX, chart choices, loading states and error handling.\n"
            "Aimable: [TBD] Manual sort vs built-in sort; when O(n^2) is acceptable.\n"
            "Eloi: Early report structure tracks real decisions; docs/project_notes.md "
            "captures team input as work progresses rather than generic filler.\n\n"
            "[TBD - Team] What we would add with more time: borough map using taxi_zones "
            "shapefiles, additional months of TLC data, and a /api/trips/ranked endpoint "
            "powered by the DSA module."
        ),
    },
]


class ReportPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(100, 100, 100)
            self.cell(0, 6, TITLE, align="L")
            self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_heading(self, title: str):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(20, 40, 80)
        self.ln(3)
        self.multi_cell(0, 6, title)
        self.ln(1)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.2, text)
        self.ln(2)


def build_pdf():
    pdf = ReportPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(22, 22, 22)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(20, 40, 80)
    pdf.ln(8)
    pdf.multi_cell(0, 10, TITLE, align="C")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)
    pdf.multi_cell(0, 5, SUBTITLE, align="C")
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 5, DATE, align="C")
    pdf.ln(6)

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(30, 30, 30)
    team_line = "  |  ".join(f"{n} ({r.split(',')[0]})" for n, r in TEAM)
    pdf.multi_cell(0, 4, team_line, align="C")
    pdf.ln(4)
    pdf.set_draw_color(20, 40, 80)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(4)

    # Sections flow across pages (~3 pages total)
    for i, section in enumerate(SECTIONS):
        if section["title"].startswith("4."):
            pdf.add_page()
        pdf.section_heading(section["title"])
        pdf.body_text(section["body"])

    pdf.output(str(OUTPUT))
    print(f"Generated {OUTPUT} ({OUTPUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    build_pdf()
