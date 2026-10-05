const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const getAuthHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('access_token')}`,
});

// ─── ALL NODES ────────────────────────────────────────────
export const fetchTransportNodes = async () => {
  const res = await fetch(`${BASE_URL}/transport/`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Transport nodes fetch failed');
  return res.json();
};

export const fetchNodeById = async (id) => {
  const res = await fetch(`${BASE_URL}/transport/${id}/`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Node not found');
  return res.json();
};

// ─── NEARBY ───────────────────────────────────────────────
// Returns { count, radius_km, by_type, results }. `by_type` is what the legend
// counts from, so the numbers reflect the area around the traveller rather than
// the whole imported catalogue.
export const fetchNearbyNodes = async (lat, lon, radiusKm = 10) => {
  const qs = new URLSearchParams({
    lat: String(lat),
    lon: String(lon),
    radius_km: String(radiusKm),
    limit: '300',
  });
  const res = await fetch(`${BASE_URL}/transport/nearby/?${qs}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Nearby fetch failed');
  return res.json();
};

/**
 * Ask the backend to import transport hubs for an area on demand.
 * The catalogue is only as complete as what has been fetched, so arriving
 * somewhere new needs the app to pull that area in.
 *
 * This returns as soon as the job is queued. A 25 km area is a few hundred
 * rate-limited Overpass requests, so the import outlives any single HTTP
 * request; use `waitForAreaImport` to follow it to completion.
 */
export const loadAreaTransport = async ({ lat, lon, place, radiusKm = 25 } = {}) => {
  const res = await fetch(`${BASE_URL}/transport/load_area/`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      ...(lat !== undefined && lon !== undefined ? { lat, lon } : {}),
      ...(place ? { place } : {}),
      radius_km: radiusKm,
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || 'Could not load transport for this area');
  }
  return data;
};

/** One poll of a queued import. */
export const fetchAreaImportStatus = async (jobId) => {
  const res = await fetch(`${BASE_URL}/transport/load_area_status/?job_id=${jobId}`, {
    headers: getAuthHeaders(),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Lost track of the import');
  return data;
};

/**
 * Poll a queued import until it finishes, reporting progress as it goes.
 *
 * Bounded on purpose: the button would otherwise spin forever if the job record
 * were ever lost, and a traveller who walked away should not keep the browser
 * polling a shared free API forever on their behalf.
 */
export const waitForAreaImport = async (jobId, onProgress, { timeoutMs = 15 * 60 * 1000 } = {}) => {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    await new Promise((r) => setTimeout(r, 2500));
    const state = await fetchAreaImportStatus(jobId);
    onProgress?.(state);
    if (state.status === 'done') return state;
    if (state.status === 'error') throw new Error(state.message || 'The import failed');
  }
  throw new Error('The import is taking longer than expected. Stops may still arrive shortly.');
};

// ─── ROUTE ────────────────────────────────────────────────
// One request per travel mode, because the routers differ: a pedestrian, a
// cyclist and a car are not sent down the same path. The endpoint takes either
// the simple start/end pair or an ordered `waypoints` list for a multi-stop trip.
export const fetchRoute = async (startLat, startLon, endLat, endLon, profile = 'car') => {
  const qs = new URLSearchParams({
    start_lat: startLat,
    start_lon: startLon,
    end_lat: endLat,
    end_lon: endLon,
    profile,
  });
  const res = await fetch(`${BASE_URL}/transport/route/?${qs}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Route fetch failed');
  return res.json();
};

/**
 * Plan a trip through an ordered list of [[lat, lon], ...] stops.
 * `points` must have at least two entries.
 */
export const fetchMultiRoute = async (points, profile = 'car') => {
  if (!points || points.length < 2) {
    throw new Error('At least two stops are needed');
  }
  const waypoints = points.map(([lat, lon]) => `${lat},${lon}`).join(';');
  const qs = new URLSearchParams({ waypoints, profile });
  const res = await fetch(`${BASE_URL}/transport/route/?${qs}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Route fetch failed');
  return res.json();
};

/**
 * "Smart" suggestion: ask every mode at once and rank them.
 *
 * Cheapest is not fastest, and fastest is not always what a budget traveller
 * wants, so the caller gets the full comparison and picks. Modes are requested
 * together so one unreachable router does not lose the others.
 */
export const fetchRouteOptions = async (points) => {
  const profiles = ['car', 'bike', 'walk'];
  const settled = await Promise.allSettled(
    profiles.map((profile) => fetchMultiRoute(points, profile)),
  );
  const options = settled
    .map((result, i) =>
      result.status === 'fulfilled'
        ? { profile: profiles[i], ok: true, ...result.value }
        : { profile: profiles[i], ok: false },
    )
    .filter((o) => o.ok);

  if (!options.length) throw new Error('No route could be calculated');

  const fastest = options.reduce((a, b) => (b.duration_min < a.duration_min ? b : a));
  const shortest = options.reduce((a, b) => (b.distance_km < a.distance_km ? b : a));

  return {
    options,
    fastest: fastest.profile,
    shortest: shortest.profile,
    recommended: fastest.profile === shortest.profile ? fastest.profile : shortest.profile,
  };
};

// ─── OSRM Open Source Routing (client-side) ───────────────
export const fetchOSRMRoute = async (startLat, startLon, endLat, endLon) => {
  const url = `https://router.project-osrm.org/route/v1/driving/${startLon},${startLat};${endLon},${endLat}?overview=full&geometries=geojson`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('OSRM route failed');
  return res.json();
};

// ─── Nominatim Geocoding (OpenStreetMap) ──────────────────
// Tuned for house numbers. The default view returns an unspecified "best
// match", which for "12 MG Road" is often the road centroid or the whole city.
// Asking for structured address details plus a bounded view, and preferring the
// most specific hit, is what turns a house number into a real doorstep pin.
//
// Every hit also carries a `precision` so the UI can say when the result is
// only street- or city-level rather than pretending it is exact.
const PRECISION_RANK = {
  building: 6,
  house: 5,
  'house_number': 5,
  entrance: 4,
  street: 3,
  road: 3,
  neighbourhood: 2,
  suburb: 2,
  city: 1,
  town: 1,
  village: 1,
  county: 0,
  state: 0,
  country: 0,
};

const rankOf = (hit) => {
  const byType = PRECISION_RANK[hit.type];
  if (byType !== undefined) return byType;
  const cat = `${hit.category || ''} ${hit.class || ''}`.trim();
  if (cat.includes('building')) return 6;
  if (cat.includes('place') && /house|building|residential/.test(cat)) return 5;
  if (cat.includes('highway')) return 3;
  if (cat.includes('place')) return 1;
  return 1;
};

/**
 * A small real bounding box around a point, for biasing Nominatim.
 *
 * It has to be a genuine rectangle. Passing the same coordinate twice, as
 * `lon,lat,lon,lat`, is not a degenerate-but-tolerated box — Nominatim rejects
 * it with HTTP 400 and every lookup fails, which looked exactly like the
 * geocoder being broken.
 *
 * The box is deliberately not used with `bounded`, so it only reorders results
 * towards the traveller's area; it never hides a legitimate match elsewhere.
 */
const biasViewbox = (lat, lon, km = 0.7) => {
  const dLat = km / 111;
  const dLon = km / (111 * Math.cos((lat * Math.PI) / 180) || 1);
  return `${(lon - dLon).toFixed(5)},${(lat + dLat).toFixed(5)},${((
    lon + dLon
  ).toFixed(5))},${(lat - dLat).toFixed(5)}`;
};

export const geocodeAddress = async (query, { near, countrycodes } = {}) => {
  const params = new URLSearchParams({
    q: query,
    format: 'jsonv2',
    // Needed for house numbers: without addressdetails Nominatim often cannot
    // tell whether it matched a building or a whole street.
    addressdetails: '1',
    limit: '10',
    'accept-language': 'en',
  });
  if (countrycodes) params.set('countrycodes', countrycodes);
  // Bias towards the traveller's own area so a repeated street name does not
  // resolve to the same street in another city.
  if (near?.[0] != null && near?.[1] != null) {
    params.set('viewbox', biasViewbox(near[0], near[1]));
  }

  const res = await fetch(
    `https://nominatim.openstreetmap.org/search?${params.toString()}`,
    { headers: { 'Accept-Language': 'en' } },
  );
  if (!res.ok) {
    // 400 here means the query itself was rejected, not that nothing matched.
    // Surfacing it as "not found" would tell the traveller to retype a query
    // that was perfectly valid.
    throw new Error(
      res.status === 400
        ? 'The address could not be searched. Try spelling it differently.'
        : 'Address lookup is busy right now. Try again in a moment.'
    );
  }
  const hits = await res.json();

  return hits
    .map((hit) => {
      const a = hit.address || {};
      return {
        ...hit,
        lat: hit.lat,
        lon: hit.lon,
        // A house number is only meaningful if Nominatim actually matched the
        // number, not just the street name.
        house_number: a.house_number || null,
        street: a.road || a.neighbourhood || a.suburb || null,
        rank: rankOf(hit),
        precision:
          a.house_number && (hit.type === 'building' || hit.category === 'building')
            ? 'exact'
            : a.house_number
              ? 'house'
              : hit.type === 'highway' || hit.category === 'highway'
                ? 'street'
                : 'area',
      };
    })
    .sort((x, y) => y.rank - x.rank);
};

export const reverseGeocode = async (lat, lon) => {
  const url = `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Reverse geocoding failed');
  return res.json();
};
