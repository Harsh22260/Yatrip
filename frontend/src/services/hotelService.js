const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token');
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
};

// ─── HOTELS ───────────────────────────────────────────────
export const fetchHotels = async () => {
  const res = await fetch(`${BASE_URL}/hotels/`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Hotels fetch failed');
  const data = await res.json();
  return data.results || data;
};

export const fetchHotelById = async (id) => {
  const res = await fetch(`${BASE_URL}/hotels/${id}/`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Hotel not found');
  return res.json();
};

// ─── Business: Create Hotel ───────────────────────────────
export const createHotel = async (payload) => {
  const res = await fetch(`${BASE_URL}/hotels/`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(JSON.stringify(err));
  }
  return res.json();
};

export const updateHotel = async (id, payload) => {
  const res = await fetch(`${BASE_URL}/hotels/${id}/`, {
    method: 'PATCH',
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(JSON.stringify(err));
  }
  return res.json();
};

// ─── Business: My Hotels ──────────────────────────────────
export const fetchMyHotels = async () => {
  const res = await fetch(`${BASE_URL}/hotels/?mine=true`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Failed to fetch your hotels');
  const data = await res.json();
  return data.results || data;
};

// ─── Business: Room Types ─────────────────────────────────
export const createRoomType = async (payload) => {
  const res = await fetch(`${BASE_URL}/room-types/`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(JSON.stringify(err));
  }
  return res.json();
};

// ─── ROOM TYPES ───────────────────────────────────────────
export const fetchRoomTypes = async (hotelId) => {
  const url = hotelId
    ? `${BASE_URL}/room-types/?hotel=${hotelId}`
    : `${BASE_URL}/room-types/`;
  const res = await fetch(url, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Room types fetch failed');
  const data = await res.json();
  return data.results || data;
};

// ─── RATE PLANS ───────────────────────────────────────────
export const fetchRatePlans = async (roomTypeId) => {
  const url = roomTypeId
    ? `${BASE_URL}/rate-plans/?room_type=${roomTypeId}`
    : `${BASE_URL}/rate-plans/`;
  const res = await fetch(url, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Rate plans fetch failed');
  const data = await res.json();
  return data.results || data;
};

// ─── BOOKINGS ─────────────────────────────────────────────
export const createBooking = async (payload) => {
  const res = await fetch(`${BASE_URL}/bookings/`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || 'Booking failed');
  }
  return res.json();
};

export const confirmBooking = async (bookingId, holdToken) => {
  const res = await fetch(`${BASE_URL}/bookings/${bookingId}/confirm/`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ hold_token: holdToken }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || 'Confirm failed');
  }
  return res.json();
};

export const cancelBooking = async (bookingId) => {
  const res = await fetch(`${BASE_URL}/bookings/${bookingId}/cancel/`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || 'Cancel failed');
  }
  return res.json();
};

export const fetchMyBookings = async () => {
  const res = await fetch(`${BASE_URL}/bookings/`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Bookings fetch failed');
  const data = await res.json();
  return data.results || data;
};