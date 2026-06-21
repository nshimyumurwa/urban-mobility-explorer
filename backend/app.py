from flask import Flask, jsonify, request
from flask_cors import CORS
from db import (
    get_db_connection,
    init_db,
    get_table_counts,
    is_db_ready,
    SCHEMA
)
from seed import seed_database
import sqlite3

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found", "message": str(e)}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error", "message": str(e)}), 500


@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": "Bad request", "message": str(e)}), 400


def _safe_float(val, default=None):
    if val is None or val == '':
        return default
    try:
        return float(val)
    except ValueError:
        return default


def _safe_int(val, default=None):
    if val is None or val == '':
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _paginated_response(rows, page, per_page, total):
    return jsonify({
        "data": [dict(r) for r in rows],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page
        }
    })


@app.route('/api/health', methods=['GET'])
def health():
    counts = get_table_counts()
    return jsonify({
        "status": "ok",
        "db_ready": is_db_ready(),
        "table_counts": counts,
        "schema": SCHEMA
    })


@app.route('/api/trips', methods=['GET'])
def get_trips():
    conn = get_db_connection()

    borough = request.args.get('borough')
    zone = request.args.get('zone')
    pickup_zone = request.args.get('pickup_zone')
    dropoff_zone = request.args.get('dropoff_zone')
    min_fare = _safe_float(request.args.get('min_fare'))
    max_fare = _safe_float(request.args.get('max_fare'))
    min_distance = _safe_float(request.args.get('min_distance'))
    max_distance = _safe_float(request.args.get('max_distance'))
    min_duration = _safe_float(request.args.get('min_duration'))
    max_duration = _safe_float(request.args.get('max_duration'))
    passenger_count = _safe_int(request.args.get('passenger_count'))
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    hour = _safe_int(request.args.get('hour'))
    time_of_day = request.args.get('time_of_day')
    sort_by = request.args.get('sort_by', 'pickup_datetime')
    sort_order = request.args.get('sort_order', 'desc')
    page = max(1, _safe_int(request.args.get('page'), 1))
    per_page = min(500, max(1, _safe_int(request.args.get('per_page'), 50)))

    allowed_sort = {
        'pickup_datetime', 'dropoff_datetime', 'fare_amount',
        'trip_distance', 'trip_duration_minutes', 'passenger_count',
        'speed_mph'
    }
    if sort_by not in allowed_sort:
        sort_by = 'pickup_datetime'
    if sort_order.lower() not in {'asc', 'desc'}:
        sort_order = 'desc'

    query = '''
        SELECT t.*,
               pz.borough as pickup_borough, pz.zone as pickup_zone,
               dz.borough as dropoff_borough, dz.zone as dropoff_zone
        FROM trips t
        LEFT JOIN zones pz ON t.pickup_location_id = pz.location_id
        LEFT JOIN zones dz ON t.dropoff_location_id = dz.location_id
        WHERE 1=1
    '''
    params = []

    if borough:
        query += ' AND pz.borough = ?'
        params.append(borough)
    if zone:
        query += ' AND (pz.zone = ? OR dz.zone = ?)'
        params.extend([zone, zone])
    if pickup_zone:
        query += ' AND pz.zone = ?'
        params.append(pickup_zone)
    if dropoff_zone:
        query += ' AND dz.zone = ?'
        params.append(dropoff_zone)
    if min_fare is not None:
        query += ' AND t.fare_amount >= ?'
        params.append(min_fare)
    if max_fare is not None:
        query += ' AND t.fare_amount <= ?'
        params.append(max_fare)
    if min_distance is not None:
        query += ' AND t.trip_distance >= ?'
        params.append(min_distance)
    if max_distance is not None:
        query += ' AND t.trip_distance <= ?'
        params.append(max_distance)
    if min_duration is not None:
        query += ' AND t.trip_duration_minutes >= ?'
        params.append(min_duration)
    if max_duration is not None:
        query += ' AND t.trip_duration_minutes <= ?'
        params.append(max_duration)
    if passenger_count is not None:
        query += ' AND t.passenger_count = ?'
        params.append(passenger_count)
    if start_date:
        query += " AND date(t.pickup_datetime) >= date(?)"
        params.append(start_date)
    if end_date:
        query += " AND date(t.pickup_datetime) <= date(?)"
        params.append(end_date)
    if hour is not None:
        query += " AND CAST(strftime('%H', t.pickup_datetime) AS INTEGER) = ?"
        params.append(hour)
    if time_of_day:
        tod_map = {
            'morning': (6, 12),
            'afternoon': (12, 17),
            'evening': (17, 21),
            'night': (21, 6)
        }
        tod = time_of_day.lower()
        if tod in tod_map:
            start_h, end_h = tod_map[tod]
            if start_h < end_h:
                query += " AND CAST(strftime('%H', t.pickup_datetime) AS INTEGER) >= ? AND CAST(strftime('%H', t.pickup_datetime) AS INTEGER) < ?"
                params.extend([start_h, end_h])
            else:
                query += " AND (CAST(strftime('%H', t.pickup_datetime) AS INTEGER) >= ? OR CAST(strftime('%H', t.pickup_datetime) AS INTEGER) < ?)"
                params.extend([start_h, end_h])

    count_query = f"SELECT COUNT(*) as total FROM ({query})"
    total = conn.execute(count_query, params).fetchone()['total']

    query += f' ORDER BY t.{sort_by} {sort_order.upper()}'
    query += ' LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])

    trips = conn.execute(query, params).fetchall()
    conn.close()

    return _paginated_response(trips, page, per_page, total)


@app.route('/api/trips/<int:trip_id>', methods=['GET'])
def get_trip(trip_id):
    conn = get_db_connection()
    trip = conn.execute('''
        SELECT t.*,
               pz.borough as pickup_borough, pz.zone as pickup_zone,
               dz.borough as dropoff_borough, dz.zone as dropoff_zone
        FROM trips t
        LEFT JOIN zones pz ON t.pickup_location_id = pz.location_id
        LEFT JOIN zones dz ON t.dropoff_location_id = dz.location_id
        WHERE t.id = ?
    ''', (trip_id,)).fetchone()
    conn.close()
    if trip is None:
        return jsonify({"error": "Trip not found"}), 404
    return jsonify(dict(trip))


@app.route('/api/summary', methods=['GET'])
def get_summary():
    conn = get_db_connection()
    stats = conn.execute('''
        SELECT
            COUNT(*) as total_trips,
            ROUND(AVG(trip_distance), 2) as avg_distance,
            ROUND(AVG(fare_amount), 2) as avg_fare,
            ROUND(AVG(trip_duration_minutes), 2) as avg_duration,
            ROUND(AVG(passenger_count), 2) as avg_passengers,
            ROUND(SUM(fare_amount), 2) as total_fare_revenue,
            ROUND(MIN(fare_amount), 2) as min_fare,
            ROUND(MAX(fare_amount), 2) as max_fare,
            ROUND(MIN(trip_distance), 2) as min_distance,
            ROUND(MAX(trip_distance), 2) as max_distance
        FROM trips
    ''').fetchone()
    conn.close()
    return jsonify(dict(stats))


@app.route('/api/summary/by-borough', methods=['GET'])
def summary_by_borough():
    conn = get_db_connection()
    data = conn.execute('''
        SELECT
            pz.borough,
            COUNT(*) as trip_count,
            ROUND(AVG(t.fare_amount), 2) as avg_fare,
            ROUND(SUM(t.fare_amount), 2) as total_fare,
            ROUND(AVG(t.trip_distance), 2) as avg_distance,
            ROUND(AVG(t.trip_duration_minutes), 2) as avg_duration
        FROM trips t
        LEFT JOIN zones pz ON t.pickup_location_id = pz.location_id
        WHERE pz.borough IS NOT NULL
        GROUP BY pz.borough
        ORDER BY trip_count DESC
    ''').fetchall()
    conn.close()
    return jsonify([dict(r) for r in data])


@app.route('/api/summary/by-hour', methods=['GET'])
def summary_by_hour():
    conn = get_db_connection()
    data = conn.execute('''
        SELECT
            CAST(strftime('%H', pickup_datetime) AS INTEGER) as hour,
            COUNT(*) as trip_count,
            ROUND(AVG(fare_amount), 2) as avg_fare,
            ROUND(SUM(fare_amount), 2) as total_fare,
            ROUND(AVG(trip_distance), 2) as avg_distance
        FROM trips
        GROUP BY hour
        ORDER BY hour
    ''').fetchall()
    conn.close()
    return jsonify([dict(r) for r in data])


@app.route('/api/summary/by-time-of-day', methods=['GET'])
def summary_by_time_of_day():
    conn = get_db_connection()
    data = conn.execute('''
        SELECT
            CASE
                WHEN CAST(strftime('%H', pickup_datetime) AS INTEGER) >= 6
                     AND CAST(strftime('%H', pickup_datetime) AS INTEGER) < 12 THEN 'Morning'
                WHEN CAST(strftime('%H', pickup_datetime) AS INTEGER) >= 12
                     AND CAST(strftime('%H', pickup_datetime) AS INTEGER) < 17 THEN 'Afternoon'
                WHEN CAST(strftime('%H', pickup_datetime) AS INTEGER) >= 17
                     AND CAST(strftime('%H', pickup_datetime) AS INTEGER) < 21 THEN 'Evening'
                ELSE 'Night'
            END as time_of_day,
            COUNT(*) as trip_count,
            ROUND(AVG(fare_amount), 2) as avg_fare,
            ROUND(SUM(fare_amount), 2) as total_fare,
            ROUND(AVG(trip_distance), 2) as avg_distance
        FROM trips
        GROUP BY time_of_day
        ORDER BY
            CASE time_of_day
                WHEN 'Morning' THEN 1
                WHEN 'Afternoon' THEN 2
                WHEN 'Evening' THEN 3
                WHEN 'Night' THEN 4
            END
    ''').fetchall()
    conn.close()
    return jsonify([dict(r) for r in data])


@app.route('/api/summary/by-zone', methods=['GET'])
def summary_by_zone():
    conn = get_db_connection()
    top_n = min(50, max(1, _safe_int(request.args.get('limit'), 10)))
    data = conn.execute('''
        SELECT
            pz.zone,
            pz.borough,
            COUNT(*) as trip_count,
            ROUND(AVG(t.fare_amount), 2) as avg_fare,
            ROUND(SUM(t.fare_amount), 2) as total_fare,
            ROUND(AVG(t.trip_distance), 2) as avg_distance
        FROM trips t
        LEFT JOIN zones pz ON t.pickup_location_id = pz.location_id
        WHERE pz.zone IS NOT NULL
        GROUP BY pz.zone, pz.borough
        ORDER BY trip_count DESC
        LIMIT ?
    ''', (top_n,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in data])


@app.route('/api/zones', methods=['GET'])
def get_zones():
    conn = get_db_connection()
    borough_filter = request.args.get('borough')
    query = 'SELECT * FROM zones WHERE 1=1'
    params = []
    if borough_filter:
        query += ' AND borough = ?'
        params.append(borough_filter)
    query += ' ORDER BY borough, zone'
    zones = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(z) for z in zones])


@app.route('/api/zones/<int:zone_id>', methods=['GET'])
def get_zone(zone_id):
    conn = get_db_connection()
    zone = conn.execute('SELECT * FROM zones WHERE location_id = ?', (zone_id,)).fetchone()
    conn.close()
    if zone is None:
        return jsonify({"error": "Zone not found"}), 404
    return jsonify(dict(zone))


@app.route('/api/exclusions', methods=['GET'])
def get_exclusions():
    conn = get_db_connection()
    limit = min(1000, max(1, _safe_int(request.args.get('limit'), 100)))
    data = conn.execute('''
        SELECT * FROM exclusion_log ORDER BY created_at DESC LIMIT ?
    ''', (limit,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in data])


@app.route('/api/admin/seed', methods=['POST'])
def admin_seed():
    force_synthetic = request.args.get('force_synthetic', 'false').lower() == 'true'
    try:
        result = seed_database(force_synthetic=force_synthetic)
        return jsonify({"message": "Database seeded successfully", "counts": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    if not is_db_ready():
        print("Database not ready. Initializing and seeding...")
        seed_database()
    app.run(debug=True, port=5000)
