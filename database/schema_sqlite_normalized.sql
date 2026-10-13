PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS exclusion_log;
DROP TABLE IF EXISTS trip_metrics;
DROP TABLE IF EXISTS trip_fares;
DROP TABLE IF EXISTS trips;
DROP TABLE IF EXISTS payment_types;
DROP TABLE IF EXISTS rate_codes;
DROP TABLE IF EXISTS vendors;
DROP TABLE IF EXISTS zones;

CREATE TABLE zones (
    location_id INTEGER PRIMARY KEY,
    borough TEXT NOT NULL,
    zone TEXT NOT NULL,
    service_zone TEXT
);

CREATE TABLE vendors (
    vendor_id INTEGER PRIMARY KEY,
    vendor_name TEXT NOT NULL
);

CREATE TABLE rate_codes (
    rate_code_id INTEGER PRIMARY KEY,
    rate_code_name TEXT NOT NULL
);

CREATE TABLE payment_types (
    payment_type_id INTEGER PRIMARY KEY,
    payment_type_name TEXT NOT NULL
);

CREATE TABLE trips (
    trip_id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id INTEGER,
    pickup_datetime TEXT NOT NULL,
    dropoff_datetime TEXT NOT NULL,
    pickup_location_id INTEGER NOT NULL,
    dropoff_location_id INTEGER NOT NULL,
    rate_code_id INTEGER,
    payment_type_id INTEGER,
    passenger_count INTEGER NOT NULL CHECK (passenger_count BETWEEN 1 AND 6),
    trip_distance REAL NOT NULL CHECK (trip_distance > 0 AND trip_distance <= 100),
    store_and_fwd_flag TEXT,
    FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id),
    FOREIGN KEY (pickup_location_id) REFERENCES zones(location_id),
    FOREIGN KEY (dropoff_location_id) REFERENCES zones(location_id),
    FOREIGN KEY (rate_code_id) REFERENCES rate_codes(rate_code_id),
    FOREIGN KEY (payment_type_id) REFERENCES payment_types(payment_type_id)
);

CREATE TABLE trip_fares (
    trip_id INTEGER PRIMARY KEY,
    fare_amount REAL NOT NULL CHECK (fare_amount > 0 AND fare_amount <= 500),
    extra REAL DEFAULT 0,
    mta_tax REAL DEFAULT 0,
    tip_amount REAL DEFAULT 0,
    tolls_amount REAL DEFAULT 0,
    improvement_surcharge REAL DEFAULT 0,
    congestion_surcharge REAL DEFAULT 0,
    airport_fee REAL DEFAULT 0,
    total_amount REAL NOT NULL,
    FOREIGN KEY (trip_id) REFERENCES trips(trip_id) ON DELETE CASCADE
);

CREATE TABLE trip_metrics (
    trip_id INTEGER PRIMARY KEY,
    trip_duration_minutes REAL NOT NULL CHECK (trip_duration_minutes > 0 AND trip_duration_minutes <= 360),
    fare_per_mile REAL NOT NULL CHECK (fare_per_mile >= 0),
    speed_mph REAL NOT NULL CHECK (speed_mph >= 0 AND speed_mph <= 120),
    pickup_hour INTEGER NOT NULL CHECK (pickup_hour BETWEEN 0 AND 23),
    pickup_weekday INTEGER NOT NULL CHECK (pickup_weekday BETWEEN 0 AND 6),
    FOREIGN KEY (trip_id) REFERENCES trips(trip_id) ON DELETE CASCADE
);

CREATE TABLE exclusion_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    row_index INTEGER,
    reason TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_trips_pickup_datetime ON trips (pickup_datetime);
CREATE INDEX idx_trips_dropoff_datetime ON trips (dropoff_datetime);
CREATE INDEX idx_trips_pickup_location ON trips (pickup_location_id);
CREATE INDEX idx_trips_dropoff_location ON trips (dropoff_location_id);
CREATE INDEX idx_trip_fares_total_amount ON trip_fares (total_amount);
CREATE INDEX idx_trip_metrics_pickup_hour ON trip_metrics (pickup_hour);
