"""
Data Pipeline for NYC TLC Trip Data
------------------------------------
Loads .parquet trip data, associates with zone lookups and spatial metadata,
cleans/integrates data, derives features, and logs exclusions.

Derived Features:
1. trip_duration_minutes  – total trip time (informs congestion / route efficiency)
2. fare_per_mile          – cost efficiency metric (identifies premium vs budget routes)
3. speed_mph              – average speed (reveals traffic patterns by time/location)
"""

import pandas as pd
import numpy as np
import sqlite3
import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'database', 'mobility.db')
SCHEMA_PATH = os.path.join(BASE_DIR, 'database', 'schema.sql')
DATA_DIR = os.path.join(BASE_DIR, 'data')

ZONES_CSV = os.path.join(DATA_DIR, 'taxi_zone_lookup.csv')
ZONES_GEOJSON_DIR = os.path.join(DATA_DIR, 'taxi_zones')


def get_parquet_paths():
    """Find all yellow_tripdata .parquet files in the data directory."""
    import glob
    return sorted(glob.glob(os.path.join(DATA_DIR, 'yellow_tripdata_*.parquet')))


def load_zone_lookup():
    """Load and standardize the taxi zone lookup CSV."""
    df = pd.read_csv(ZONES_CSV)
    df.columns = [c.lower() for c in df.columns]
    df = df.rename(columns={'locationid': 'location_id', 'servicezone': 'service_zone'})
    df['location_id'] = df['location_id'].astype(int)
    return df


def load_spatial_metadata():
    """Load taxi_zones GeoJSON metadata if available."""
    geojson_path = os.path.join(DATA_DIR, 'taxi_zones.geojson')
    if os.path.exists(geojson_path):
        with open(geojson_path, 'r') as f:
            return json.load(f)
    geojson_path = os.path.join(DATA_DIR, 'taxi_zones.json')
    if os.path.exists(geojson_path):
        with open(geojson_path, 'r') as f:
            return json.load(f)

    shapefiles = [f for f in os.listdir(ZONES_GEOJSON_DIR) if f.endswith('.shp')] \
        if os.path.isdir(ZONES_GEOJSON_DIR) else []
    if shapefiles:
        try:
            import geopandas as gpd
            gdf = gpd.read_file(os.path.join(ZONES_GEOJSON_DIR, shapefiles[0]))
            return json.loads(gdf.to_json())
        except ImportError:
            pass

    return None


def load_trip_data(filepath, nrows=None):
    """Load a .parquet trip file, returning a DataFrame."""
    print(f"Loading: {os.path.basename(filepath)}")
    df = pd.read_parquet(filepath)
    if nrows:
        df = df.head(nrows)
    return df


def standardize_columns(df):
    """Rename columns to lowercase/snake_case and keep relevant ones."""
    df.columns = [c.lower() for c in df.columns]
    rename_map = {
        'tpep_pickup_datetime': 'pickup_datetime',
        'tpep_dropoff_datetime': 'dropoff_datetime',
        'pulocationid': 'pickup_location_id',
        'dolocationid': 'dropoff_location_id',
        'ratecodeid': 'rate_code_id',
        'payment_type': 'payment_type',
        'vendorid': 'vendor_id',
        'airport_fee': 'airport_fee',
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    return df


def clean_and_validate(df, filename="unknown", exclusion_log=None):
    """
    Clean the DataFrame: remove nulls, outliers, invalid records.
    Returns (cleaned_df, exclusion_log).
    """
    if exclusion_log is None:
        exclusion_log = []

    total_rows = len(df)
    excluded_rows = []

    def _exclude(idx, reason, details=""):
        excluded_rows.append({
            'filename': filename,
            'row_index': int(idx) if pd.notna(idx) else None,
            'reason': reason,
            'details': str(details)[:200]
        })

    # --- 1. Missing values ---
    required_cols = [
        'pickup_datetime', 'dropoff_datetime',
        'passenger_count', 'trip_distance',
        'pickup_location_id', 'dropoff_location_id',
        'fare_amount', 'total_amount'
    ]
    existing_required = [c for c in required_cols if c in df.columns]
    null_mask = df[existing_required].isnull().any(axis=1)
    null_indices = df.index[null_mask].tolist()
    for idx in null_indices:
        _exclude(idx, "missing_values", f"Null in required columns: {existing_required}")
    df = df[~null_mask]

    # --- 2. Duplicates ---
    dup_cols = [c for c in ['pickup_datetime', 'dropoff_datetime', 'pickup_location_id',
                             'dropoff_location_id', 'fare_amount', 'trip_distance']
                if c in df.columns]
    if dup_cols:
        dup_mask = df.duplicated(subset=dup_cols, keep='first')
        dup_indices = df.index[dup_mask].tolist()
        for idx in dup_indices:
            _exclude(idx, "duplicate", f"Duplicate on: {dup_cols}")
        df = df[~dup_mask]

    # --- 3. Outlier detection: fare_amount ---
    for col, lo, hi in [
        ('fare_amount', 0, 500),
        ('trip_distance', 0, 100),
        ('passenger_count', 1, 6),
    ]:
        if col not in df.columns:
            continue
        mask = ~((df[col] > lo) & (df[col] <= hi))
        outlier_indices = df.index[mask].tolist()
        for idx in outlier_indices:
            _exclude(idx, f"outlier_{col}", f"{col}={df.loc[idx, col]}, range=({lo}, {hi}]")
        df = df[~mask]

    # --- 4. Temporal outliers ---
    df['pickup_datetime'] = pd.to_datetime(df['pickup_datetime'], errors='coerce')
    df['dropoff_datetime'] = pd.to_datetime(df['dropoff_datetime'], errors='coerce')

    time_null = df['pickup_datetime'].isnull() | df['dropoff_datetime'].isnull()
    for idx in df.index[time_null].tolist():
        _exclude(idx, "invalid_datetime", "Could not parse datetime")
    df = df[~time_null]

    dropoff_before_pickup = df['dropoff_datetime'] <= df['pickup_datetime']
    for idx in df.index[dropoff_before_pickup].tolist():
        _exclude(idx, "negative_duration",
                 f"dropoff={df.loc[idx, 'dropoff_datetime']}, pickup={df.loc[idx, 'pickup_datetime']}")
    df = df[~dropoff_before_pickup]

    # --- 5. Duration outliers ---
    duration_minutes = (df['dropoff_datetime'] - df['pickup_datetime']).dt.total_seconds() / 60
    duration_mask = (duration_minutes <= 0) | (duration_minutes > 360)
    for idx in df.index[duration_mask].tolist():
        _exclude(idx, "outlier_duration",
                 f"duration_minutes={duration_minutes.loc[idx]:.1f}, valid=(0, 360]")
    df = df[~duration_mask]

    # --- 6. IQR-based fare/distance ratio outliers ---
    ratio = df['fare_amount'] / df['trip_distance'].replace(0, np.nan)
    Q1 = ratio.quantile(0.01)
    Q3 = ratio.quantile(0.99)
    IQR = Q3 - Q1
    ratio_mask = (ratio < (Q1 - 1.5 * IQR)) | (ratio > (Q3 + 1.5 * IQR))
    for idx in df.index[ratio_mask].tolist():
        _exclude(idx, "outlier_fare_per_distance",
                 f"fare/distance={ratio.loc[idx]:.2f}, IQR bounds=({Q1 - 1.5*IQR:.2f}, {Q3 + 1.5*IQR:.2f})")
    df = df[~ratio_mask]

    exclusions = pd.DataFrame(excluded_rows) if excluded_rows else pd.DataFrame()
    print(f"  Total rows     : {total_rows}")
    print(f"  Excluded rows  : {len(excluded_rows)}")
    print(f"  Remaining rows : {len(df)}")
    if not exclusions.empty:
        print(f"  Exclusion breakdown:")
        print(exclusions['reason'].value_counts().to_string())

    return df, exclusions


def engineer_features(df):
    """
    Add derived features to the DataFrame.

    Feature 1: trip_duration_minutes
        - Total elapsed time from pickup to dropoff.
        - Why: Core metric for congestion analysis, route efficiency, and pricing.

    Feature 2: fare_per_mile
        - Total fare divided by distance.
        - Why: Reveals cost efficiency — high values indicate short premium trips
          (e.g., airport runs), low values indicate long budget trips.

    Feature 3: speed_mph
        - Average speed (trip_distance / duration in hours).
        - Why: Proxy for traffic congestion; lower speeds = dense urban / rush hour,
          higher speeds = highway / late-night.
    """
    df['trip_duration_minutes'] = round(
        (df['dropoff_datetime'] - df['pickup_datetime']).dt.total_seconds() / 60, 2
    )

    df['fare_per_mile'] = round(
        df['fare_amount'] / df['trip_distance'].replace(0, np.nan), 2
    )

    df['speed_mph'] = round(
        df['trip_distance'] / (df['trip_duration_minutes'] / 60), 2
    )
    df['speed_mph'] = df['speed_mph'].fillna(0).clip(0, 120)

    return df


def normalize_for_db(df):
    """Normalize data types for SQLite storage."""
    df['pickup_datetime'] = df['pickup_datetime'].astype(str)
    df['dropoff_datetime'] = df['dropoff_datetime'].astype(str)
    numeric_cols = [
        'passenger_count', 'trip_distance', 'fare_amount',
        'tip_amount', 'total_amount', 'trip_duration_minutes',
        'fare_per_mile', 'speed_mph', 'pickup_location_id', 'dropoff_location_id'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df


def get_trip_columns():
    """Return the columns inserted into the trips table (matches schema)."""
    return [
        'pickup_datetime', 'dropoff_datetime', 'passenger_count',
        'trip_distance', 'pickup_location_id', 'dropoff_location_id',
        'fare_amount', 'tip_amount', 'total_amount',
        'trip_duration_minutes', 'fare_per_mile', 'speed_mph'
    ]


def run_pipeline(parquet_paths=None, nrows=None):
    """
    Run the full pipeline: load, clean, feature-engineer, and insert.

    If parquet_paths is None, auto-detect parquet files in data/.
    If none found, falls back to synthetic data.
    """
    from db import init_db, get_db_connection

    zones = load_zone_lookup()
    spatial = load_spatial_metadata()

    if spatial:
        print(f"Loaded spatial metadata: {len(spatial.get('features', []))} zones")
    print(f"Loaded zone lookup: {len(zones)} zones")

    all_exclusions = []
    total_trips = 0

    if parquet_paths is None:
        parquet_paths = get_parquet_paths()

    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Clear existing data
    conn.execute("DELETE FROM trips")
    conn.execute("DELETE FROM exclusion_log")

    # Insert zones fresh
    zones.to_sql('zones', conn, if_exists='replace', index=False)

    if parquet_paths:
        for fpath in parquet_paths:
            try:
                df = load_trip_data(fpath, nrows=nrows)
            except Exception as e:
                print(f"  Error loading {fpath}: {e}")
                continue

            df = standardize_columns(df)
            df, exclusions = clean_and_validate(df, os.path.basename(fpath))
            df = engineer_features(df)
            df = normalize_for_db(df)

            cols = get_trip_columns()
            rows = df[cols].to_numpy().tolist()
            placeholders = ", ".join(["?"] * len(cols))
            col_names = ", ".join(cols)
            conn.executemany(
                f"INSERT INTO trips ({col_names}) VALUES ({placeholders})",
                rows
            )
            total_trips += len(df)
            all_exclusions.append(exclusions)
    else:
        print("No parquet files found. Use seed_database() for synthetic data.")

    # Save exclusion log
    if all_exclusions:
        excl_df = pd.concat(all_exclusions, ignore_index=True)
        excl_df.to_sql('exclusion_log', conn, if_exists='append', index=False)
        print(f"\nTotal records excluded: {len(excl_df)}")
        print(f"Exclusions saved to exclusion_log table.")

    conn.commit()
    conn.close()

    print(f"\nPipeline complete. {total_trips} trips inserted.")
    return {"zones": len(zones), "trips": total_trips}


if __name__ == '__main__':
    run_pipeline()
