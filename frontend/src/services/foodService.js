const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const getAuthHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('access_token')}`,
});

// ─── VENDORS ──────────────────────────────────────────────
export const fetchVendors = async () => {
  const res = await fetch(`${BASE_URL}/food/`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Vendors fetch failed');
  return res.json();
};

export const fetchVendorById = async (id) => {
  const res = await fetch(`${BASE_URL}/food/${id}/`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Vendor not found');
  return res.json();
};

export const fetchNearbyVendors = async (lat, lon) => {
  const res = await fetch(
    `${BASE_URL}/food/nearby/?lat=${lat}&lon=${lon}`,
    { headers: getAuthHeaders() }
  );
  if (!res.ok) throw new Error('Nearby fetch failed');
  return res.json();
};

// ─── CATEGORIES ───────────────────────────────────────────
export const fetchFoodCategories = async () => {
  const res = await fetch(`${BASE_URL}/food/categories/`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Categories fetch failed');
  return res.json();
};

// ─── MENU ITEMS ───────────────────────────────────────────
export const fetchMenuItems = async (vendorId) => {
  const res = await fetch(
    `${BASE_URL}/food/menu/?vendor=${vendorId}`,
    { headers: getAuthHeaders() }
  );
  if (!res.ok) throw new Error('Menu fetch failed');
  return res.json();
};
