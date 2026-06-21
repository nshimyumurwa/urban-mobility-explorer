/**
 * api.js
 * -----------------------------------------------------------------
 * Thin wrapper around the backend's REST endpoints. Nothing in this
 * file touches the DOM — it only knows how to talk to the API and
 * throw a readable Error if something goes wrong.
 *
 * Backend repo: /backend/app.py (Flask, SQLite). If your teammate's
 * server runs on a different host/port, change API_BASE below and
 * nothing else needs to change.
 *
 * Trimmed down to the three endpoints the simplified dashboard
 * (filters + summary cards + hourly chart) actually uses. The
 * backend still exposes /api/summary/*, /api/exclusions, etc. — add
 * a method back here if a future feature needs one of them again.
 * -----------------------------------------------------------------
 */

const API_BASE = 'http://127.0.0.1:5000';

/**
 * GET helper. Builds a query string from `params`, skipping any
 * empty/undefined values so we don't send `?borough=` to the API.
 */
async function apiGet(path, params = {}) {
  const url = new URL(API_BASE + path);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== '' && value !== null && value !== undefined) {
      url.searchParams.set(key, value);
    }
  });

  let res;
  try {
    res = await fetch(url.toString());
  } catch (networkErr) {
    throw new Error(
      `Could not reach the API at ${API_BASE}. Is the Flask server running on port 5000?`
    );
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message || body.error || `Request failed (${res.status})`);
  }

  return res.json();
}

const Api = {
  health: () => apiGet('/api/health'),
  zones: (borough) => apiGet('/api/zones', { borough }),
  trips: (params) => apiGet('/api/trips', params),
};