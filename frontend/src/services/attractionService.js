const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const getAuthHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('access_token')}`,
});

// ─── ALL ATTRACTIONS ──────────────────────────────────────
export const fetchAttractions = async () => {
  const res = await fetch(`${BASE_URL}/attractions/`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Attractions fetch failed');
  return res.json();
};

export const fetchAttractionById = async (id) => {
  const res = await fetch(`${BASE_URL}/attractions/${id}/`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Attraction not found');
  return res.json();
};

// ─── NEARBY ───────────────────────────────────────────────
export const fetchNearbyAttractions = async (lat, lon) => {
  const res = await fetch(
    `${BASE_URL}/attractions/nearby/?lat=${lat}&lon=${lon}`,
    { headers: getAuthHeaders() }
  );
  if (!res.ok) throw new Error('Nearby fetch failed');
  return res.json();
};

// ─── BY CITY ──────────────────────────────────────────────
export const fetchAttractionsByCity = async (city) => {
  const res = await fetch(
    `${BASE_URL}/attractions/city/?name=${encodeURIComponent(city)}`,
    { headers: getAuthHeaders() }
  );
  if (!res.ok) throw new Error('City fetch failed');
  return res.json();
};
