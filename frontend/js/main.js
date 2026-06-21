/**
 * main.js
 * -----------------------------------------------------------------
 * App entry point. Holds state, wires up the filter form, and
 * orchestrates fetching + rendering for the simplified dashboard:
 * filters → summary cards → hourly demand chart → peak hours.
 *
 * Why this no longer calls /api/summary or /api/summary/by-hour:
 * those endpoints return totals across the WHOLE dataset with no
 * filter support, so they'd silently ignore "Apply filters" and the
 * page would look broken. /api/trips DOES respect filters, so every
 * stat here is derived from one /api/trips call instead.
 *
 * Total Trips is always exact — it comes straight from
 * pagination.total, which the backend computes over the full
 * filtered set regardless of page size. Everything else (avg fare,
 * avg distance, avg duration, avg tip %, total revenue, and the
 * hourly breakdown) is computed client-side from the trips actually
 * returned, capped at SAMPLE_SIZE (the backend's per-page max).
 * When the filtered set is larger than that, those cards are
 * labeled "sample of N" rather than presented as exact — Total
 * Revenue specifically becomes an estimate (avg × total count) in
 * that case, also labeled.
 * -----------------------------------------------------------------
 */

const SAMPLE_SIZE = 500;

const state = {
  filters: {},
};

// ---------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------

const currencyFmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
const numberFmt = new Intl.NumberFormat('en-US');
const timeFmt = new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit' });

function fmtCurrency(v) { return v == null ? '—' : currencyFmt.format(v); }
function fmtNumber(v) { return v == null ? '—' : numberFmt.format(v); }
function fmtDecimal(v, d = 2) { return v == null || Number.isNaN(Number(v)) ? '—' : Number(v).toFixed(d); }
function fmtPercent(v, d = 1) { return v == null ? '—' : `${Number(v).toFixed(d)}%`; }

// ---------------------------------------------------------------
// Status / error UI
// ---------------------------------------------------------------

function setConnectionStatus(ok) {
  const light = document.getElementById('statusLight');
  const text = document.getElementById('statusText');
  light.classList.toggle('is-ok', ok);
  light.classList.toggle('is-error', !ok);
  text.textContent = ok ? 'Connected' : 'API unreachable';
}

function showErrorBanner(message, retryFn) {
  const banner = document.getElementById('errorBanner');
  document.getElementById('errorBannerText').textContent = message;
  banner.hidden = false;
  const retryBtn = document.getElementById('errorBannerRetry');
  retryBtn.onclick = () => {
    banner.hidden = true;
    retryFn && retryFn();
  };
}

function hideErrorBanner() {
  document.getElementById('errorBanner').hidden = true;
}

function setChartStatus(id, message) {
  const el = document.getElementById(id);
  if (!el) return;
  if (message === null) {
    el.classList.add('is-hidden');
    return;
  }
  el.textContent = message;
  el.classList.remove('is-hidden');
  el.classList.toggle('is-error', /unable|fail|error/i.test(message));
}

function updateLastUpdatedLabel() {
  const el = document.getElementById('filtersLastUpdated');
  if (el) el.textContent = `Last updated ${timeFmt.format(new Date())}`;
}

// ---------------------------------------------------------------
// KPI meters
// ---------------------------------------------------------------

function setMeter(id, value, sub = '') {
  const valueEl = document.querySelector(`#${id} .meter__value`);
  if (!valueEl) return;
  valueEl.textContent = value;
  valueEl.removeAttribute('data-skeleton');
  const subEl = document.querySelector(`#${id} .meter__sub`);
  if (subEl) subEl.textContent = sub;
}

/**
 * Walks one page of /api/trips rows and reduces them into:
 *  - averages for fare, distance, duration, tip %, and total amount
 *  - a 24-row hourly breakdown (hour, trip_count, avg_fare), shaped
 *    exactly like the old /api/summary/by-hour response so
 *    renderHourChart() in charts.js didn't need to change.
 */
function computeStatsFromTrips(trips) {
  let fareSum = 0, fareN = 0;
  let distSum = 0, distN = 0;
  let durSum = 0, durN = 0;
  let tipPctSum = 0, tipPctN = 0;
  let totalSum = 0, totalN = 0;

  const hourly = {}; // hour -> { trip_count, fareSum }

  trips.forEach(t => {
    const fare = Number(t.fare_amount);
    const hasFare = !Number.isNaN(fare);
    if (hasFare) { fareSum += fare; fareN++; }

    const dist = Number(t.trip_distance);
    if (!Number.isNaN(dist)) { distSum += dist; distN++; }

    const dur = Number(t.trip_duration_minutes);
    if (!Number.isNaN(dur)) { durSum += dur; durN++; }

    const tip = Number(t.tip_amount);
    if (hasFare && fare > 0 && !Number.isNaN(tip)) {
      tipPctSum += (tip / fare) * 100;
      tipPctN++;
    }

    const total = Number(t.total_amount);
    if (!Number.isNaN(total)) { totalSum += total; totalN++; }

    const hour = t.pickup_datetime ? Number(t.pickup_datetime.slice(11, 13)) : NaN;
    if (!Number.isNaN(hour)) {
      if (!hourly[hour]) hourly[hour] = { trip_count: 0, fareSum: 0 };
      hourly[hour].trip_count++;
      if (hasFare) hourly[hour].fareSum += fare;
    }
  });

  const hourRows = [];
  for (let h = 0; h < 24; h++) {
    const bucket = hourly[h];
    hourRows.push({
      hour: h,
      trip_count: bucket ? bucket.trip_count : 0,
      avg_fare: bucket && bucket.trip_count ? bucket.fareSum / bucket.trip_count : 0,
    });
  }

  return {
    avgFare: fareN ? fareSum / fareN : null,
    avgDistance: distN ? distSum / distN : null,
    avgDuration: durN ? durSum / durN : null,
    avgTipPct: tipPctN ? tipPctSum / tipPctN : null,
    avgTotalAmount: totalN ? totalSum / totalN : null,
    hourRows,
  };
}

function renderSummaryCards(totalTrips, stats, sampled) {
  const note = sampled ? `sample of ${fmtNumber(SAMPLE_SIZE)}` : '';

  setMeter('meterTrips', fmtNumber(totalTrips));
  setMeter('meterFare', fmtCurrency(stats.avgFare), note);
  setMeter('meterDistance', stats.avgDistance != null ? `${fmtDecimal(stats.avgDistance)} mi` : '—', note);
  setMeter('meterDuration', stats.avgDuration != null ? `${fmtDecimal(stats.avgDuration, 1)} min` : '—', note);
  setMeter('meterTipPct', fmtPercent(stats.avgTipPct), note);

  // Total Revenue is an exact sum when every matching trip was
  // actually fetched (filtered total <= SAMPLE_SIZE); otherwise it's
  // an estimate extrapolated from the sample's average — labeled
  // accordingly rather than presented as exact.
  if (stats.avgTotalAmount != null) {
    const revenue = stats.avgTotalAmount * totalTrips;
    setMeter('meterRevenue', fmtCurrency(revenue), sampled ? `estimated · ${note}` : '');
  } else {
    setMeter('meterRevenue', 'n/a');
  }
}

// ---------------------------------------------------------------
// Peak Hours (manual insertion sort from sort.js)
// ---------------------------------------------------------------

function renderPeakHours(hourRows) {
  const list = document.getElementById('peakHoursList');
  if (!list) return;

  const ranked = sortTrips(hourRows, 'trip_count', 'desc');
  const top = ranked.filter(r => r.trip_count > 0).slice(0, 3);

  if (top.length === 0) {
    list.innerHTML = '<li class="ranking-item"><span class="ranking-item__label">No trips match the current filters</span></li>';
    return;
  }

  list.innerHTML = top.map(r => `
    <li class="ranking-item">
      <span class="ranking-item__label">${String(r.hour).padStart(2, '0')}:00</span>
      <span class="ranking-item__value">${fmtNumber(r.trip_count)} trips</span>
    </li>
  `).join('');
}

// ---------------------------------------------------------------
// Filters
// ---------------------------------------------------------------

function readFiltersFromForm() {
  const form = document.getElementById('filterForm');
  const data = new FormData(form);
  const filters = {};
  for (const [key, value] of data.entries()) {
    if (value !== '') filters[key] = value;
  }
  return filters;
}

function wireFilterForm() {
  const form = document.getElementById('filterForm');
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    state.filters = readFiltersFromForm();
    loadDashboard();
  });

  document.getElementById('resetFiltersBtn').addEventListener('click', () => {
    form.reset();
    state.filters = {};
    loadDashboard();
  });
}

async function loadBoroughOptions() {
  try {
    const zones = await Api.zones();
    const boroughs = [...new Set(zones.map(z => z.borough))].filter(Boolean).sort();
    const select = document.getElementById('filterBorough');
    boroughs.forEach(b => {
      const opt = document.createElement('option');
      opt.value = b;
      opt.textContent = b;
      select.appendChild(opt);
    });
  } catch (err) {
    console.error('zones failed (borough dropdown stays at "All")', err);
  }
}

// ---------------------------------------------------------------
// Main load — single /api/trips call drives cards + chart + ranking
// ---------------------------------------------------------------

async function loadDashboard() {
  setChartStatus('hourChartStatus', 'Loading…');
  document.querySelectorAll('.meter__value').forEach(el => el.setAttribute('data-skeleton', ''));

  try {
    const res = await Api.trips({
      ...state.filters,
      per_page: SAMPLE_SIZE,
      page: 1,
      sort_by: 'pickup_datetime',
      sort_order: 'desc',
    });

    const trips = res.data;
    const totalTrips = res.pagination.total;
    const sampled = totalTrips > trips.length;

    const stats = computeStatsFromTrips(trips);
    renderSummaryCards(totalTrips, stats, sampled);

    renderHourChart(stats.hourRows);
    setChartStatus('hourChartStatus', null);
    renderPeakHours(stats.hourRows);

    const peak = stats.hourRows.reduce((max, r) => (r.trip_count > max.trip_count ? r : max), stats.hourRows[0]);
    const hourInsightEl = document.getElementById('hourInsight');
    if (peak && peak.trip_count > 0) {
      const peakLabel = `${String(peak.hour).padStart(2, '0')}:00`;
      hourInsightEl.textContent = `Peak demand is around ${peakLabel} with ${fmtNumber(peak.trip_count)} trips and an average fare of ${fmtCurrency(peak.avg_fare)}${sampled ? ' (based on a sample of the filtered trips)' : ''}.`;
    } else {
      hourInsightEl.textContent = 'No trips match the current filters.';
    }

    document.getElementById('tripsSampleNote').textContent = sampled
      ? `Based on the ${fmtNumber(trips.length)} most recent of ${fmtNumber(totalTrips)} matching trips`
      : '';

    updateLastUpdatedLabel();
  } catch (err) {
    setChartStatus('hourChartStatus', 'Unable to load this chart.');
    document.querySelectorAll('.meter__value').forEach(el => { el.textContent = 'n/a'; el.removeAttribute('data-skeleton'); });
    console.error('dashboard load failed', err);
  }
}

// ---------------------------------------------------------------
// Boot
// ---------------------------------------------------------------

async function init() {
  wireFilterForm();

  try {
    await Api.health();
    setConnectionStatus(true);
    hideErrorBanner();
  } catch (err) {
    setConnectionStatus(false);
    showErrorBanner(err.message, init);
    return; // don't bother hitting other endpoints if the API is down
  }

  loadBoroughOptions();
  loadDashboard();
}

document.addEventListener('DOMContentLoaded', init);