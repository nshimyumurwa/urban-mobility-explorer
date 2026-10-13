"""
Database seeding script.

Attempts to load real NYC TLC .parquet data.
If no parquet files are found, falls back to synthetic data.
"""

import pandas as pd
import random
from datetime import datetime, timedelta
from db import get_db_connection, init_db
from data_pipeline import (
    run_pipeline, get_parquet_paths, load_zone_lookup, load_zones,
    clean_and_validate, engineer_features, normalize_for_db, insert_cleaned_trips
)



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
        distance = max(0.5, random.gauss(3, 4))
        distance = round(min(distance, 25), 2)
        duration = max(duration, distance / 2 + 1 / 60)
        dropoff = pickup + timedelta(minutes=duration)

        fare = distance * random.gauss(4, 1) + random.gauss(2.5, 0.5)
        fare = max(2.5, min(fare, 150))

        tip = fare * random.uniform(0.05, 0.25)
        total = fare + tip + 0.5 + 0.3
        pu = random.choice(zone_ids)
        do = random.choice(zone_ids)

        records.append({
            'pickup_datetime': pickup.strftime('%Y-%m-%d %H:%M:%S'),
            'dropoff_datetime': dropoff.strftime('%Y-%m-%d %H:%M:%S'),
            'passenger_count': random.randint(1, 4),
            'trip_distance': distance,
            'pickup_location_id': pu,
            'dropoff_location_id': do,
            'fare_amount': round(fare, 2),
            'tip_amount': round(tip, 2),
            'total_amount': round(total, 2),
            'mta_tax': 0.5,
            'improvement_surcharge': 0.3,
        })

    df, exclusions = clean_and_validate(
        pd.DataFrame(records), 'synthetic', valid_zone_ids=set(zone_ids)
    )
    df = normalize_for_db(engineer_features(df))
    inserted = insert_cleaned_trips(conn, df, 'synthetic')
    conn.executemany(
        "INSERT INTO exclusion_log (filename, row_index, reason, details) VALUES (?, ?, ?, ?)",
        exclusions.itertuples(index=False, name=None),
    )
    print(f"Inserted {inserted} synthetic trips")
    return inserted


def seed_database(force_synthetic=False):
    """
    Seed the database with real parquet data if available, else synthetic.
    """
    parquet_files = get_parquet_paths()
    if not force_synthetic and parquet_files:
        print(f"Found {len(parquet_files)} parquet file(s). Running pipeline...")
        result = run_pipeline(parquet_paths=parquet_files)
    else:
        print("Using explicitly requested synthetic data." if force_synthetic
              else "No parquet files found. Using synthetic data.")
        init_db()
        conn = get_db_connection()
        try:
            with conn:
                conn.execute("DELETE FROM trips")
                conn.execute("DELETE FROM exclusion_log")
                conn.execute("DELETE FROM zones")
                for table in ['vendors', 'rate_codes', 'payment_types']:
                    conn.execute(f"DELETE FROM {table}")
                zones = load_zone_lookup()
                load_zones(conn, zones)
                print(f"Loaded {len(zones)} zones")
                trips_count = generate_synthetic_trips(conn)
        finally:
            conn.close()
        result = {"zones": len(zones), "trips": trips_count}

    print("Database ready!")
    return result


if __name__ == '__main__':
    seed_database()
