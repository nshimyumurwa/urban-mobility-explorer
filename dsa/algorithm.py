"""
Custom DSA Implementation: Insertion Sort for Trip Ranking
----------------------------------------------------------
This module manually implements an insertion sort algorithm to rank
NYC taxi trips by fare amount without using any built-in sorting
functions or libraries.

Problem it solves:
    Given a list of trip records, we need to identify the most and
    least expensive trips across different boroughs. Built-in functions
    like sort() or sorted() are not used anywhere in this implementation.

Time Complexity:
    Best case:  O(n)     - when the list is already sorted
    Worst case: O(n^2)   - when the list is sorted in reverse order
    Average:    O(n^2)

Space Complexity:
    O(1) - sorting is done in place, no extra memory needed

Pseudo-code:
    for i from 1 to length(trips):
        current = trips[i]
        j = i - 1
        while j >= 0 and trips[j][key] > current[key]:
            trips[j + 1] = trips[j]
            j = j - 1
        trips[j + 1] = current
    return trips
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'mobility.db')


def insertion_sort_by_fare(trip_list):
    """
    Manually sorts a list of trip dictionaries by fare_amount
    using the insertion sort algorithm.

    No built-in sort(), sorted(), or any sorting library is used.

    Parameters:
        trip_list (list): A list of trip dictionaries, each containing
                          at least a 'fare_amount' key.

    Returns:
        list: The same list sorted in ascending order by fare_amount.
    """
    for i in range(1, len(trip_list)):
        current_trip = trip_list[i]
        current_fare = current_trip['fare_amount']
        j = i - 1

        while j >= 0 and trip_list[j]['fare_amount'] > current_fare:
            trip_list[j + 1] = trip_list[j]
            j -= 1

        trip_list[j + 1] = current_trip

    return trip_list


def get_top_expensive_trips(n=10):
    """
    Retrieves the top n most expensive trips from the database
    using the custom insertion sort instead of SQL ORDER BY.

    Parameters:
        n (int): Number of top trips to return. Default is 10.

    Returns:
        list: Top n trips sorted by fare amount in descending order.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute('''
        SELECT t.fare_amount, t.trip_distance, t.trip_duration_minutes,
               t.passenger_count, t.fare_per_mile,
               pz.borough as pickup_borough,
               dz.borough as dropoff_borough
        FROM trips t
        LEFT JOIN zones pz ON t.pickup_location_id = pz.location_id
        LEFT JOIN zones dz ON t.dropoff_location_id = dz.location_id
        LIMIT 500
    ''').fetchall()

    conn.close()

    trip_list = [dict(row) for row in rows]

    sorted_trips = insertion_sort_by_fare(trip_list)

    top_n = []
    for i in range(len(sorted_trips) - 1, len(sorted_trips) - 1 - n, -1):
        if i >= 0:
            top_n.append(sorted_trips[i])

    return top_n


def get_cheapest_trips(n=10):
    """
    Retrieves the n cheapest trips using the custom insertion sort.

    Parameters:
        n (int): Number of cheapest trips to return. Default is 10.

    Returns:
        list: Bottom n trips sorted by fare amount in ascending order.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute('''
        SELECT t.fare_amount, t.trip_distance, t.trip_duration_minutes,
               t.passenger_count, t.fare_per_mile,
               pz.borough as pickup_borough,
               dz.borough as dropoff_borough
        FROM trips t
        LEFT JOIN zones pz ON t.pickup_location_id = pz.location_id
        LEFT JOIN zones dz ON t.dropoff_location_id = dz.location_id
        LIMIT 500
    ''').fetchall()

    conn.close()

    trip_list = [dict(row) for row in rows]
    sorted_trips = insertion_sort_by_fare(trip_list)

    return sorted_trips[:n]


def benchmark(sample_size=100):
    """
    Demonstrates the insertion sort working on a sample of trips
    and prints the results to the console.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(f'''
        SELECT fare_amount, trip_distance, trip_duration_minutes
        FROM trips
        LIMIT {sample_size}
    ''').fetchall()

    conn.close()

    trip_list = [dict(row) for row in rows]

    print(f"Running insertion sort on {sample_size} trips...")
    print(f"First fare before sorting: {trip_list[0]['fare_amount']}")

    sorted_trips = insertion_sort_by_fare(trip_list)

    print(f"First fare after sorting:  {sorted_trips[0]['fare_amount']}")
    print(f"Last fare after sorting:   {sorted_trips[-1]['fare_amount']}")
    print(f"Sorting complete. {len(sorted_trips)} trips ranked by fare amount.")
    print()
    print("Top 5 most expensive trips:")
    for i in range(len(sorted_trips) - 1, len(sorted_trips) - 6, -1):
        t = sorted_trips[i]
        print(f"  Fare: ${t['fare_amount']} | Distance: {t['trip_distance']} mi | Duration: {t['trip_duration_minutes']} min")

    print()
    print("Top 5 cheapest trips:")
    for t in sorted_trips[:5]:
        print(f"  Fare: ${t['fare_amount']} | Distance: {t['trip_distance']} mi | Duration: {t['trip_duration_minutes']} min")


if __name__ == '__main__':
    benchmark()