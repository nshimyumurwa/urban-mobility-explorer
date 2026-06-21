/**
 * sort.js
 * -----------------------------------------------------------------
 * Assignment requirement: "manually implement at least one algorithm
 * or data structure... without relying on built-in libraries or
 * prewritten logic." This is that piece — a hand-written insertion
 * sort. It does NOT use Array.prototype.sort anywhere.
 *
 * Originally this sorted the Trip Explorer table by column. That
 * table was removed when the dashboard was simplified down to
 * filters + summary cards + an hourly chart, so insertionSort now
 * orders the 24 hourly buckets by trip_count to drive the "Peak
 * Hours" list under the chart (see renderPeakHours in main.js). The
 * sort itself is unchanged — only what gets fed into it changed.
 *
 * Time complexity:  O(n^2) worst case, O(n) best case (nearly sorted)
 * Space complexity: O(n) — we copy the input array instead of
 *                    mutating it in place, so the caller's reference
 *                    stays untouched.
 * -----------------------------------------------------------------
 */

/**
 * Sorts `arr` using insertion sort. `compareFn(a, b)` should return
 * a positive number if `a` belongs after `b`, negative if before,
 * zero if equal — same contract as Array.prototype.sort's comparator,
 * we just never call that built-in.
 */
function insertionSort(arr, compareFn) {
  const result = arr.slice(); // don't mutate the caller's array

  for (let i = 1; i < result.length; i++) {
    const current = result[i];
    let j = i - 1;

    while (j >= 0 && compareFn(result[j], current) > 0) {
      result[j + 1] = result[j];
      j--;
    }
    result[j + 1] = current;
  }

  return result;
}

/**
 * Field-aware comparator for trip-shaped objects (works for both the
 * raw /api/trips rows and the synthetic per-hour buckets built in
 * main.js, since both are plain objects with numeric fields).
 * Numeric fields are coerced to Number so "9" doesn't sort after
 * "10"; datetime strings sort correctly as plain strings because the
 * API returns them in ISO-ish "YYYY-MM-DD HH:MM:SS" order.
 */
const NUMERIC_TRIP_KEYS = new Set([
  'trip_distance', 'fare_amount', 'tip_amount', 'total_amount',
  'trip_duration_minutes', 'speed_mph', 'fare_per_mile', 'passenger_count',
  'trip_count', 'hour', 'avg_fare'
]);

function compareTrips(a, b, key, direction) {
  let va = a[key];
  let vb = b[key];

  if (NUMERIC_TRIP_KEYS.has(key)) {
    va = Number(va) || 0;
    vb = Number(vb) || 0;
  }

  let cmp = 0;
  if (va > vb) cmp = 1;
  else if (va < vb) cmp = -1;

  return direction === 'desc' ? -cmp : cmp;
}

/** Convenience wrapper used by main.js */
function sortTrips(trips, key, direction) {
  return insertionSort(trips, (a, b) => compareTrips(a, b, key, direction));
}