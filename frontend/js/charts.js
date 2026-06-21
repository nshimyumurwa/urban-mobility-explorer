/**
 * charts.js
 * -----------------------------------------------------------------
 * One render function per chart. It destroys the previous Chart.js
 * instance (if any) before drawing a new one, so calling it again
 * after a filter change just redraws cleanly instead of stacking
 * canvases on top of each other.
 *
 * Trimmed down to the single chart the simplified dashboard shows
 * (trip demand by hour). The borough/time-of-day/efficiency chart
 * renderers were removed along with their panels — pull them back
 * out of version control if those panels come back.
 * -----------------------------------------------------------------
 */

const GRID_COLOR = '#efe8e2';

// Shared Chart.js defaults so the chart matches the light dispatch-
// board theme instead of Chart.js's own dark defaults.
Chart.defaults.color = '#6e6660';
Chart.defaults.borderColor = '#e8e1da';
Chart.defaults.font.family = "'IBM Plex Mono', monospace";
Chart.defaults.font.size = 11;

const chartInstances = {};

function destroyIfExists(id) {
  if (chartInstances[id]) {
    chartInstances[id].destroy();
    delete chartInstances[id];
  }
}

/**
 * Trip demand throughout the day — dual axis: volume (area) + avg
 * fare (line). Expects 24 rows shaped { hour, trip_count, avg_fare },
 * one per hour 0–23 (see computeStatsFromTrips in main.js).
 */
function renderHourChart(rows) {
  destroyIfExists('hour');
  const ctx = document.getElementById('hourChart').getContext('2d');

  const labels = rows.map(r => `${String(r.hour).padStart(2, '0')}:00`);

  chartInstances.hour = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Trips',
          data: rows.map(r => r.trip_count),
          borderColor: '#7b1e3d',
          backgroundColor: 'rgba(123, 30, 61, 0.10)',
          fill: true,
          tension: 0.35,
          yAxisID: 'y',
          pointRadius: 0,
          borderWidth: 2,
        },
        {
          label: 'Avg fare ($)',
          data: rows.map(r => r.avg_fare),
          borderColor: '#dc8b2b',
          backgroundColor: 'transparent',
          fill: false,
          tension: 0.35,
          yAxisID: 'y1',
          pointRadius: 0,
          borderWidth: 1.5,
          borderDash: [4, 3],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        y: { position: 'left', title: { display: true, text: 'Trips' }, grid: { color: GRID_COLOR } },
        y1: { position: 'right', title: { display: true, text: 'Avg fare ($)' }, grid: { display: false } },
        x: { grid: { display: false } },
      },
      plugins: { legend: { position: 'top', labels: { boxWidth: 10 } } },
    },
  });
}