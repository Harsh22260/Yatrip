const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const getAuthHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('access_token')}`,
});

// ─── RENTALS ──────────────────────────────────────────────
export const fetchRentals = async () => {
  const res = await fetch(`${BASE_URL}/rentals/`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Rentals fetch failed');
  return res.json();
};

export const fetchRentalById = async (id) => {
  const res = await fetch(`${BASE_URL}/rentals/${id}/`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Rental not found');
  return res.json();
};

export const fetchNearbyRentals = async (lat, lon) => {
  const res = await fetch(
    `${BASE_URL}/rentals/nearby/?lat=${lat}&lon=${lon}`,
    { headers: getAuthHeaders() }
  );
  if (!res.ok) throw new Error('Nearby fetch failed');
  return res.json();
};

// ─── AMENITIES ────────────────────────────────────────────
export const fetchAmenities = async () => {
  const res = await fetch(`${BASE_URL}/rentals/amenities/`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Amenities fetch failed');
  return res.json();
};
