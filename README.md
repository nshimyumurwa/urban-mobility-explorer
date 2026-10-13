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

### Step 5: Start the backend server

```bash
py app.py
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
| fare_per_mile | Total fare divided by trip distance | Shows cost efficiency and helps identify premium routes |
| speed_mph | Distance divided by duration converted to hours | Acts as a proxy for traffic congestion levels |

---

## Database Design

The project includes two normalized schema definitions for Part 1:

- SQLite: [schema_sqlite_normalized.sql](./database/schema_sqlite_normalized.sql)
- PostgreSQL: [schema_postgres_normalized.sql](./database/schema_postgres_normalized.sql)

These are proposed schemas; the current pipeline still loads the existing
[schema.sql](./database/schema.sql). Loading into the normalized tables is not
implemented yet. Both normalized scripts drop existing tables, so run them only
against a separate, disposable database.

Both schemas use:

- `zones` (dimension table for location metadata)
- `vendors`, `rate_codes`, `payment_types` (dimension tables for categorical IDs)
- `trips` (core trip fact table)
- `trip_fares` (1:1 fare/tax breakdown per trip)
- `trip_metrics` (1:1 derived metrics per trip)
- `exclusion_log` (cleaning transparency/audit trail)

---

## Data Cleaning Summary

The pipeline removes records with missing values in required fields, duplicate trip entries, fares outside the range of 0 to 500 dollars, trip distances above 100 miles or below 0, passenger counts below 1 or above 6, trips where dropoff time is before or equal to pickup time, and trip durations above 6 hours. All excluded records are saved to the exclusion_log table for transparency.

---

## Key Findings

- Manhattan is the origin of over 90 percent of all recorded trips in the dataset.
- Average fares during late night hours between midnight and 3am tend to be higher than during daytime.
- Average vehicle speed drops noticeably during morning rush hours between 7am and 9am, which reflects higher traffic congestion during those periods.