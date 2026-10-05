import { asList, request } from './api';

// The hotels app is mounted at /api/hotels/, and its router registers each
// resource under that prefix. The old service called /api/hotels/ and
// /api/bookings/, which do not exist and 404'd on every request.
const HOTELS = 'hotels/hotels';
const ROOM_TYPES = 'hotels/room-types';
const ROOM_UNITS = 'hotels/room-units';
const RATE_PLANS = 'hotels/rate-plans';
const AVAILABILITY = 'hotels/availability';
const BOOKINGS = 'hotels/bookings';

const withQuery = (path, params) => {
  if (!params) return path;
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.set(key, value);
  });
  const query = search.toString();
  return query ? `${path}?${query}` : path;
};

// ─── HOTELS ───────────────────────────────────────────────
export const fetchHotels = async (params) =>
  asList(await request(withQuery(HOTELS, params)));

export const fetchHotelById = async (id) => request(`${HOTELS}/${id}/`);

// ─── Business: Create / update hotel ───────────────────────
export const createHotel = async (payload) => request(HOTELS, { method: 'POST', body: payload });

export const updateHotel = async (id, payload) =>
  request(`${HOTELS}/${id}/`, { method: 'PATCH', body: payload });

export const deleteHotel = async (id) => request(`${HOTELS}/${id}/`, { method: 'DELETE' });

export const regenerateAvailability = async (id) =>
  request(`${HOTELS}/${id}/generate_availability/`, { method: 'POST' });

// ─── Business: My Hotels ───────────────────────────────────
export const fetchMyHotels = async () => asList(await request(withQuery(HOTELS, { mine: 'true' })));

// ─── Room types ───────────────────────────────────────────
export const fetchRoomTypes = async (hotelId) =>
  asList(await request(withQuery(ROOM_TYPES, { hotel: hotelId })));

export const createRoomType = async (payload) =>
  request(ROOM_TYPES, { method: 'POST', body: payload });

export const updateRoomType = async (id, payload) =>
  request(`${ROOM_TYPES}/${id}/`, { method: 'PATCH', body: payload });

export const deleteRoomType = async (id) => request(`${ROOM_TYPES}/${id}/`, { method: 'DELETE' });

// ─── Room units ───────────────────────────────────────────
export const fetchRoomUnits = async (roomTypeId) =>
  asList(await request(withQuery(ROOM_UNITS, { room_type: roomTypeId })));

export const createRoomUnit = async (payload) => request(ROOM_UNITS, { method: 'POST', body: payload });

// ─── Rate plans ───────────────────────────────────────────
export const fetchRatePlans = async (roomTypeId) =>
  asList(await request(withQuery(RATE_PLANS, { room_type: roomTypeId })));

export const createRatePlan = async (payload) => request(RATE_PLANS, { method: 'POST', body: payload });

// ─── Availability ─────────────────────────────────────────
export const fetchAvailability = async ({ roomTypeId, dateGte, dateLte } = {}) =>
  asList(
    await request(
      withQuery(AVAILABILITY, {
        room_type: roomTypeId,
        date__gte: dateGte,
        date__lte: dateLte,
      })
    )
  );

/** Advisory pre-flight check. The authoritative check happens on hold. */
export const checkAvailability = async ({ roomTypeId, checkIn, checkOut, units = 1 }) =>
  request(
    withQuery(`${BOOKINGS}/availability`, {
      room_type: roomTypeId,
      check_in: checkIn,
      check_out: checkOut,
      units,
    })
  );

// ─── Bookings ─────────────────────────────────────────────
/**
 * Create a hold. The response carries `hold_token` and `booking`; pass the
 * token to confirmBooking before it expires.
 */
export const createBooking = async (payload) =>
  request(BOOKINGS, { method: 'POST', body: payload });

export const confirmBooking = async (bookingId, holdToken) =>
  request(`${BOOKINGS}/${bookingId}/confirm/`, { method: 'POST', body: { hold_token: holdToken } });

export const cancelBooking = async (bookingId) =>
  request(`${BOOKINGS}/${bookingId}/cancel/`, { method: 'POST' });

export const fetchMyBookings = async () => asList(await request(BOOKINGS));
