import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'database', 'mobility.db')
SCHEMA_PATH = os.path.join(BASE_DIR, 'database', 'schema.sql')

SCHEMA = {
    "zones": {
        "columns": ["location_id", "borough", "zone", "service_zone"],
        "primary_key": "location_id",
        "description": "NYC taxi zone lookup with borough and service zone mappings"
    },
    "trips": {
        "columns": [
            "id", "pickup_datetime", "dropoff_datetime", "passenger_count",
            "trip_distance", "pickup_location_id", "dropoff_location_id",
            "fare_amount", "tip_amount", "total_amount",
            "trip_duration_minutes", "fare_per_mile", "speed_mph"
        ],
        "primary_key": "id",
        "foreign_keys": {
            "pickup_location_id": "zones(location_id)",
            "dropoff_location_id": "zones(location_id)"
        },
        "description": "Individual taxi trips with derived metrics like duration, fare_per_mile, and speed_mph"
    },
    "exclusion_log": {
        "columns": ["id", "filename", "row_index", "reason", "details", "created_at"],
        "primary_key": "id",
        "description": "Log of excluded or suspicious records during data cleaning"
    }
}


def get_db_connection():
    """Return a SQLite connection with Row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database from schema.sql if it doesn't exist or is empty."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, 'r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def get_table_counts():
    """Return row counts for each known table."""
    conn = get_db_connection()
    counts = {}
    for table in SCHEMA.keys():
        try:
            row = conn.execute(f"SELECT COUNT(*) as count FROM {table}").fetchone()
            counts[table] = row['count']
        except sqlite3.OperationalError:
            counts[table] = None
    conn.close()
    return counts


def table_exists(table_name):
    """Check if a table exists in the database."""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    ).fetchone()
    conn.close()
    return row is not None


def is_db_ready():
    """Check if all schema tables exist and have data."""
    if not os.path.exists(DB_PATH):
        return False
    conn = get_db_connection()
    for table in SCHEMA.keys():
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        )
        if cur.fetchone() is None:
            conn.close()
            return False
    conn.close()
    return True
