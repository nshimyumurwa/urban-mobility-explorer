"""
Database seeding script.

Attempts to load real NYC TLC .parquet data.
If no parquet files are found, falls back to synthetic data.
"""

import pandas as pd
import sqlite3
import os
import random
from datetime import datetime, timedelta
from db import DB_PATH, SCHEMA_PATH, get_db_connection, init_db
from data_pipeline import (
    run_pipeline, get_parquet_paths, load_zone_lookup, load_trip_data,
    standardize_columns, clean_and_validate, engineer_features,
    normalize_for_db, get_trip_columns
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRIPS_CSV_PATH = os.path.join(BASE_DIR, 'data', 'yellow_tripdata_2019-01.csv')


def generate_synthetic_trips(conn, count=5000):
    """Generate realistic synthetic trip data when no real data is available."""
    print(f"Generating {count} synthetic trips...")
    cursor = conn.execute("SELECT location_id, borough FROM zones")
    zones = cursor.fetchall()
    if not zones:
        raise RuntimeError("No zones found in database. Load zones first.")

    zone_ids = [z['location_id'] for z in zones]

    records = []
    base_time = datetime(2019, 1, 1, 0, 0, 0)
    for i in range(count):
        pickup = base_time + timedelta(minutes=random.randint(0, 30 * 24 * 60))
        duration = random.gauss(15, 10)
        duration = max(2, min(duration, 120))
        dropoff = pickup + timedelta(minutes=duration)

        distance = max(0.5, random.gauss(3, 4))
        distance = min(distance, 25)

        fare = distance * random.gauss(4, 1) + random.gauss(2.5, 0.5)
        fare = max(2.5, min(fare, 150))

        tip = fare * random.uniform(0.05, 0.25)
        total = fare + tip + 0.5 + 0.3
        speed = distance / (duration / 60) if duration > 0 else 0

        pu = random.choice(zone_ids)
        do = random.choice(zone_ids)

        records.append({
            'pickup_datetime': pickup.strftime('%Y-%m-%d %H:%M:%S'),
            'dropoff_datetime': dropoff.strftime('%Y-%m-%d %H:%M:%S'),
            'passenger_count': random.randint(1, 4),
            'trip_distance': round(distance, 2),
            'pickup_location_id': pu,
            'dropoff_location_id': do,
            'fare_amount': round(fare, 2),
            'tip_amount': round(tip, 2),
            'total_amount': round(total, 2),
            'trip_duration_minutes': round(duration, 2),
            'fare_per_mile': round(fare / distance, 2) if distance > 0 else 0,
            'speed_mph': round(speed, 2)
        })

    df = pd.DataFrame(records)
    conn.execute("DELETE FROM trips")
    df.to_sql('trips', conn, if_exists='append', index=False)
    print(f"Inserted {len(df)} synthetic trips")
    return len(df)


def seed_database(force_synthetic=False):
    """
    Seed the database with real parquet data if available, else synthetic.
    """
    init_db()

    parquet_files = get_parquet_paths()
    if not force_synthetic and parquet_files:
        print(f"Found {len(parquet_files)} parquet file(s). Running pipeline...")
        result = run_pipeline(parquet_paths=parquet_files)
    else:
        print("No parquet files found. Using synthetic data.")
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        init_db()

        zones = load_zone_lookup()
        zones.to_sql('zones', conn, if_exists='replace', index=False)
        print(f"Loaded {len(zones)} zones")

        trips_count = generate_synthetic_trips(conn)
        conn.commit()
        conn.close()
        result = {"zones": len(zones), "trips": trips_count}

    print("Database ready!")
    return result


if __name__ == '__main__':
    seed_database()
