import pandas as pd
import sqlite3
import os

# File paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRIPS_PATH = os.path.join(BASE_DIR, 'data', 'yellow_tripdata_2019-01.csv')
ZONES_PATH = os.path.join(BASE_DIR, 'data', 'taxi_zone_lookup.csv')
DB_PATH = os.path.join(BASE_DIR, 'database', 'mobility.db')
SCHEMA_PATH = os.path.join(BASE_DIR, 'database', 'schema.sql')

def setup_database():
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, 'r') as f:
        conn.executescript(f.read())
    conn.commit()
    return conn

def load_zones(conn):
    print("Loading zones...")
    zones = pd.read_csv(ZONES_PATH)
    zones.columns = [c.lower() for c in zones.columns]
    zones = zones.rename(columns={'locationid': 'location_id', 'servicezone': 'service_zone'})
    zones.to_sql('zones', conn, if_exists='replace', index=False)
    print(f"Loaded {len(zones)} zones")

def clean_and_load_trips(conn):
    print("Reading trips data (first 50,000 rows)...")
    df = pd.read_csv(TRIPS_PATH, nrows=50000)

    print("Cleaning data...")
    # Rename columns to lowercase
    df.columns = [c.lower() for c in df.columns]

    # Keep only needed columns
    df = df[[
        'tpep_pickup_datetime', 'tpep_dropoff_datetime',
        'passenger_count', 'trip_distance',
        'pulocationid', 'dolocationid',
        'fare_amount', 'tip_amount', 'total_amount'
    ]]

    # Rename columns
    df = df.rename(columns={
        'tpep_pickup_datetime': 'pickup_datetime',
        'tpep_dropoff_datetime': 'dropoff_datetime',
        'pulocationid': 'pickup_location_id',
        'dolocationid': 'dropoff_location_id'
    })

    # Remove nulls
    df = df.dropna()

    # Remove outliers
    df = df[df['fare_amount'] > 0]
    df = df[df['fare_amount'] < 500]
    df = df[df['trip_distance'] > 0]
    df = df[df['trip_distance'] < 100]
    df = df[df['passenger_count'] > 0]
    df = df[df['passenger_count'] <= 6]

    # Convert datetimes
    df['pickup_datetime'] = pd.to_datetime(df['pickup_datetime'])
    df['dropoff_datetime'] = pd.to_datetime(df['dropoff_datetime'])

    # --- DERIVED FEATURES ---
    # 1. Trip duration in minutes
    df['trip_duration_minutes'] = (
        df['dropoff_datetime'] - df['pickup_datetime']
    ).dt.total_seconds() / 60

    # 2. Fare per mile
    df['fare_per_mile'] = df['fare_amount'] / df['trip_distance']

    # 3. Time of day category
    df['time_of_day'] = df['pickup_datetime'].dt.hour.apply(
        lambda h: 'Morning' if 6 <= h < 12
        else 'Afternoon' if 12 <= h < 17
        else 'Evening' if 17 <= h < 21
        else 'Night'
    )

    # Remove trips with negative or very long duration
    df = df[df['trip_duration_minutes'] > 0]
    df = df[df['trip_duration_minutes'] < 180]

    # Convert datetime back to string for SQLite
    df['pickup_datetime'] = df['pickup_datetime'].astype(str)
    df['dropoff_datetime'] = df['dropoff_datetime'].astype(str)

    print(f"Clean trips remaining: {len(df)}")
    print("Inserting into database...")
    df.to_sql('trips', conn, if_exists='replace', index=False)
    print("Done!")

if __name__ == '__main__':
    conn = setup_database()
    load_zones(conn)
    clean_and_load_trips(conn)
    conn.close()
    print("Database ready!")