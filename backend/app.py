from flask import Flask, jsonify, request
from db import get_db_connection

app = Flask(__name__)

@app.route('/api/trips', methods=['GET'])
def get_trips():
    conn = get_db_connection()
    borough = request.args.get('borough')
    min_fare = request.args.get('min_fare')
    max_fare = request.args.get('max_fare')
    limit = request.args.get('limit', 100)

    query = '''
        SELECT t.*, 
               pz.borough as pickup_borough, 
               dz.borough as dropoff_borough
        FROM trips t
        LEFT JOIN zones pz ON t.pickup_location_id = pz.location_id
        LEFT JOIN zones dz ON t.dropoff_location_id = dz.location_id
        WHERE 1=1
    '''
    params = []

    if borough:
        query += ' AND pz.borough = ?'
        params.append(borough)
    if min_fare:
        query += ' AND t.fare_amount >= ?'
        params.append(float(min_fare))
    if max_fare:
        query += ' AND t.fare_amount <= ?'
        params.append(float(max_fare))

    query += ' LIMIT ?'
    params.append(int(limit))

    trips = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(t) for t in trips])


@app.route('/api/summary', methods=['GET'])
def get_summary():
    conn = get_db_connection()
    stats = conn.execute('''
        SELECT 
            COUNT(*) as total_trips,
            ROUND(AVG(trip_distance), 2) as avg_distance,
            ROUND(AVG(fare_amount), 2) as avg_fare,
            ROUND(AVG(trip_duration_minutes), 2) as avg_duration
        FROM trips
    ''').fetchone()
    conn.close()
    return jsonify(dict(stats))


@app.route('/api/trips/by-borough', methods=['GET'])
def trips_by_borough():
    conn = get_db_connection()
    data = conn.execute('''
        SELECT pz.borough, COUNT(*) as trip_count,
               ROUND(AVG(t.fare_amount), 2) as avg_fare
        FROM trips t
        LEFT JOIN zones pz ON t.pickup_location_id = pz.location_id
        GROUP BY pz.borough
        ORDER BY trip_count DESC
    ''').fetchall()
    conn.close()
    return jsonify([dict(r) for r in data])


@app.route('/api/trips/by-hour', methods=['GET'])
def trips_by_hour():
    conn = get_db_connection()
    data = conn.execute('''
        SELECT 
            CAST(strftime('%H', pickup_datetime) AS INTEGER) as hour,
            COUNT(*) as trip_count,
            ROUND(AVG(fare_amount), 2) as avg_fare
        FROM trips
        GROUP BY hour
        ORDER BY hour
    ''').fetchall()
    conn.close()
    return jsonify([dict(r) for r in data])


if __name__ == '__main__':
    app.run(debug=True, port=5000)