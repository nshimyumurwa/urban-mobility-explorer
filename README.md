# Urban Mobility Data Explorer
Team 2 | ALU Enterprise Web Development Summative Assignment

A fullstack web application that processes, stores, and visualizes New York City yellow taxi trip data. The goal is to help users explore urban mobility patterns across the five boroughs of New York City through an interactive dashboard backed by a REST API.

---

## Team Members

| Name | Role |
|------|------|
| Nshimyumurwa Mary Therese | Team Lead, Flask API, Database Design |
| Davy Dushimiyimana| Data Pipeline, Backend Support |
| Clive Mushipe | Frontend Dashboard |
| Aimable Bancunguye | DSA Implementation |
| Eloi Mizero | Documentation and Technical Report |

---

## Video Walkthrough

Watch the 5-minute project demo here: https://youtu.be/hAqCF2pQTZg

---

## Project Structure

    urban-mobility-explorer/
    ├── backend/
    │   ├── app.py
    │   ├── clean_data.py
    │   ├── data_pipeline.py
    │   ├── db.py
    │   ├── seed.py
    │   └── requirements.txt
    ├── frontend/
    │   ├── index.html
    │   └── css/
    │   └── js/
    ├── database/
    │   └── schema.sql
    ├── dsa/
    │   └── algorithm.py
    ├── data/
    │   ├── taxi_zone_lookup.csv
    │   └── taxi_zones/
    └── docs/
        └── report.pdf
---      

## Requirements

- Python 3.9 or higher
- pip (Python package installer)
- A modern web browser

---

## Installation and Setup

### Step 1: Clone the repository

```bash
git clone https://github.com/nshimyumurwa/urban-mobility-explorer.git
cd urban-mobility-explorer
```

### Step 2: Install required packages

```bash
pip install -r backend/requirements.txt
```

### Step 3: Download the dataset

Run the downloader script from the project root:

```bash
python backend/download_tlc_data.py --year 2019 --month 1
```

This downloads:

- `yellow_tripdata_2019-01.parquet`
- `taxi_zone_lookup.csv`
- `taxi_zones.zip`

All files are saved into [data/](./data/).

NYC TLC data source: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

### Step 4: Run the data cleaning pipeline

```bash
python backend/data_pipeline.py
```

This script loads `.parquet` trip data, removes missing values/duplicates/outliers, engineers three derived features, logs excluded records, and loads cleaned data into local SQLite.

It now loads the normalized schema into `database/mobility.db`. Parquet files
are streamed in batches of 100,000 rows rather than loaded entirely into memory.
To run a smaller sample first:

```bash
python backend/data_pipeline.py --nrows 10000
```

`--nrows` limits raw rows **per file**. Omit it to process every row.
Use `--db-path path/to/test.db` to write a separate database.
Each run builds and validates a new database before replacing the target. Any
existing database is backed up beside it as `mobility.db.<timestamp>.bak`;
failed runs leave the old database intact. Stop the API before rebuilding so
it has no active database connections.

### Step 5: Start the backend server

```bash
python backend/app.py
```

The API will be available at http://localhost:5000

### Step 6: Open the frontend

Open the file frontend/index.html in your browser. The dashboard will load and connect to the running API automatically.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/summary | Returns overall statistics for all trips |
| GET | /api/trips | Returns trip records with optional filters |
| GET | /api/trips/by-borough | Returns trip count and average fare per borough |
| GET | /api/trips/by-hour | Returns trip count broken down by hour of day |

### Available filters for /api/trips

- borough: filter trips by pickup borough name (example: Manhattan)
- min_fare: only return trips above this fare amount
- max_fare: only return trips below this fare amount
- limit: maximum number of results to return (default is 100)

### Example requests

```bash
# Get overall summary
curl http://localhost:5000/api/summary

# Get trips starting in Brooklyn
curl "http://localhost:5000/api/trips?borough=Brooklyn&limit=20"

# Get trips with fare between 10 and 50 dollars
curl "http://localhost:5000/api/trips?min_fare=10&max_fare=50"
```

---

## Derived Features

The data pipeline calculates three additional columns from the raw data:

| Feature | How it is calculated | What it tells us |
|---------|---------------------|-----------------|
| trip_duration_minutes | Difference between dropoff and pickup time in minutes | Measures route efficiency and time spent in traffic |
| fare_per_mile | Base fare_amount divided by trip distance | Shows cost efficiency and helps identify premium routes |
| speed_mph | Distance divided by duration converted to hours | Acts as a proxy for traffic congestion levels |

---

## Database Design

The project includes two normalized schema definitions for Part 1:

- SQLite: [schema_sqlite_normalized.sql](./database/schema_sqlite_normalized.sql)
- PostgreSQL: [schema_postgres_normalized.sql](./database/schema_postgres_normalized.sql)

The SQLite schema is used by the pipeline, API initialization, and synthetic
seeding. [schema.sql](./database/schema.sql) is the historical flat schema and
is no longer used. PostgreSQL remains a design reference, not a supported loader;
its script drops existing tables, so use it only in a disposable database.

Both schemas use:

- `zones` (dimension table for location metadata)
- `vendors`, `rate_codes`, `payment_types` (dimension tables for categorical IDs)
- `trips` (core trip fact table)
- `trip_fares` (1:1 fare/tax breakdown per trip)
- `trip_metrics` (1:1 derived metrics per trip)
- `exclusion_log` (cleaning transparency/audit trail)

`trip_fares` and `trip_metrics` share the trip's primary key, ensuring at most one
row per trip. The loader verifies that every trip has both related rows and
that foreign keys are valid. All application connections enable foreign keys.
The read-only `trip_details` view joins these tables and preserves the existing
dashboard response fields, including `id`, fare amounts, and derived metrics.
Categorical dimensions are populated from observed codes. Unmapped TLC codes
are retained with an explicit `Unmapped TLC code <id>` label; missing optional
codes and fare components remain SQL NULL, not invented zero values.
Pickup hour and weekday (Monday = 0) are stored with the derived metrics.
TLC timestamps are stored consistently as New York local, timezone-naive values.
The official `N/A` labels for zones 264 and 265 are preserved as text, not
mistaken for missing values.

---

## Data Cleaning Summary

The pipeline removes records with missing values in required fields, duplicate trip entries, fares outside the range of 0 to 500 dollars, trip distances above 100 miles or below 0, passenger counts below 1 or above 6, trips where dropoff time is before or equal to pickup time, and trip durations above 6 hours. All excluded records are saved to the exclusion_log table for transparency.

The valid limits are `(0, 500]` dollars, `(0, 100]` miles, integer passenger
counts `[1, 6]`, duration `(0, 360]` minutes, and speed at most 120 mph.
Invalid/non-finite numbers, fractional identifiers, unknown pickup/dropoff
zones, negative monetary values, and totals below the base fare are also
excluded. Missing optional monetary values are retained as NULL.
Duplicate detection uses all normalized trip and itemized fare fields, both
within batches and across batches/files. Each excluded row gets one reason,
its source filename, and its zero-based source row index.
Unlike the old pipeline, speeds are rejected rather than clipped, and the
sample-dependent fare-per-distance percentile filter has been removed to make
cleaning independent of batch size.

Full January 2019 run with these rules:

| Measure | Rows |
|---------|------|
| Raw trip records processed | 7,696,617 |
| Cleaned trips loaded | 7,465,435 |
| Excluded records logged | 231,182 |
| Taxi zones loaded | 265 |

Each cleaned trip has exactly one fare row and one metrics row. Foreign-key
validation found no violations. The most common exclusions were invalid
passenger counts (115,607), invalid distances (51,802), and required missing
values (28,672).

### Pipeline and API tests

```bash
python -m unittest discover -s backend -p 'test_*.py'
```

---

## Key Findings

- Manhattan is the origin of over 90 percent of all recorded trips in the dataset.
- Average fares during late night hours between midnight and 3am tend to be higher than during daytime.
- Average vehicle speed drops noticeably during morning rush hours between 7am and 9am, which reflects higher traffic congestion during those periods.