const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const getAuthHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('access_token')}`,
});

// ─── HOTELS ───────────────────────────────────────────────
export const fetchHotels = async () => {
  const res = await fetch(`${BASE_URL}/hotels/`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Hotels fetch failed');
  return res.json();
};

export const fetchHotelById = async (id) => {
  const res = await fetch(`${BASE_URL}/hotels/${id}/`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Hotel not found');
  return res.json();
};

// ─── ROOM TYPES ───────────────────────────────────────────
export const fetchRoomTypes = async (hotelId) => {
  const url = hotelId
    ? `${BASE_URL}/room-types/?hotel=${hotelId}`
    : `${BASE_URL}/room-types/`;
  const res = await fetch(url, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Room types fetch failed');
  return res.json();
};

// ─── RATE PLANS ───────────────────────────────────────────
export const fetchRatePlans = async (roomTypeId) => {
  const url = roomTypeId
    ? `${BASE_URL}/rate-plans/?room_type=${roomTypeId}`
    : `${BASE_URL}/rate-plans/`;
  const res = await fetch(url, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Rate plans fetch failed');
  return res.json();
};

// ─── AVAILABILITY ─────────────────────────────────────────
export const fetchAvailability = async (roomTypeId, checkIn, checkOut) => {
  let url = `${BASE_URL}/availability/?room_type=${roomTypeId}`;
  if (checkIn) url += `&date__gte=${checkIn}`;
  if (checkOut) url += `&date__lte=${checkOut}`;
  const res = await fetch(url, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Availability fetch failed');
  return res.json();
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
  return res.json();
};
