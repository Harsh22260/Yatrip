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
export const fetchNearbyNodes = async (lat, lon) => {
  const res = await fetch(
    `${BASE_URL}/transport/nearby/?lat=${lat}&lon=${lon}`,
    { headers: getAuthHeaders() }
  );
  if (!res.ok) throw new Error('Nearby fetch failed');
  return res.json();
};

// ─── ROUTE ────────────────────────────────────────────────
export const fetchRoute = async (startLat, startLon, endLat, endLon) => {
  const res = await fetch(
    `${BASE_URL}/transport/route/?start_lat=${startLat}&start_lon=${startLon}&end_lat=${endLat}&end_lon=${endLon}`,
    { headers: getAuthHeaders() }
  );
  if (!res.ok) throw new Error('Route fetch failed');
  return res.json();
};

// ─── OSRM Open Source Routing (client-side) ───────────────
export const fetchOSRMRoute = async (startLat, startLon, endLat, endLon) => {
  const url = `https://router.project-osrm.org/route/v1/driving/${startLon},${startLat};${endLon},${endLat}?overview=full&geometries=geojson`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('OSRM route failed');
  return res.json();
};

// ─── Nominatim Geocoding (OpenStreetMap) ──────────────────
export const geocodeAddress = async (query) => {
  const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=5`;
  const res = await fetch(url, { headers: { 'Accept-Language': 'en' } });
  if (!res.ok) throw new Error('Geocoding failed');
  return res.json();
};

export const reverseGeocode = async (lat, lon) => {
  const url = `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Reverse geocoding failed');
  return res.json();
};
