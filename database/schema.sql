CREATE TABLE IF NOT EXISTS zones (
    location_id INTEGER PRIMARY KEY,
    borough TEXT NOT NULL,
    zone TEXT NOT NULL,
    service_zone TEXT
);

CREATE TABLE IF NOT EXISTS trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pickup_datetime TEXT NOT NULL,
    dropoff_datetime TEXT NOT NULL,
    passenger_count INTEGER,
    trip_distance REAL,
    pickup_location_id INTEGER,
    dropoff_location_id INTEGER,
    fare_amount REAL,
    tip_amount REAL,
    total_amount REAL,
    trip_duration_minutes REAL,
    fare_per_mile REAL,
    speed_mph REAL,
    FOREIGN KEY (pickup_location_id) REFERENCES zones(location_id),
    FOREIGN KEY (dropoff_location_id) REFERENCES zones(location_id)
);

CREATE TABLE IF NOT EXISTS exclusion_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    row_index INTEGER,
    reason TEXT,
    details TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);