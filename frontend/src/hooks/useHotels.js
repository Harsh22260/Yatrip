import { useState, useEffect, useCallback } from 'react';
import {
  fetchHotels,
  fetchHotelById,
  fetchRoomTypes,
  fetchRatePlans,
  fetchAvailability,
  fetchMyBookings,
} from '../services/hotelService';

// ─── useHotels ────────────────────────────────────────────
export const useHotels = () => {
  const [hotels, setHotels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchHotels();
      setHotels(data.results || data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return { hotels, loading, error, refetch: load };
};

// ─── useHotelDetail ───────────────────────────────────────
export const useHotelDetail = (hotelId) => {
  const [hotel, setHotel] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!hotelId) return;
    setLoading(true);
    setError(null);
    fetchHotelById(hotelId)
      .then(setHotel)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [hotelId]);

  return { hotel, loading, error };
};

// ─── useRoomTypes ─────────────────────────────────────────
export const useRoomTypes = (hotelId) => {
  const [roomTypes, setRoomTypes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!hotelId) return;
    setLoading(true);
    fetchRoomTypes(hotelId)
      .then((data) => setRoomTypes(data.results || data))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [hotelId]);

  return { roomTypes, loading, error };
};

// ─── useRatePlans ─────────────────────────────────────────
export const useRatePlans = (roomTypeId) => {
  const [ratePlans, setRatePlans] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!roomTypeId) return;
    setLoading(true);
    fetchRatePlans(roomTypeId)
      .then((data) => setRatePlans(data.results || data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [roomTypeId]);

  return { ratePlans, loading };
};

// ─── useAvailability ──────────────────────────────────────
export const useAvailability = (roomTypeId, checkIn, checkOut) => {
  const [availability, setAvailability] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!roomTypeId || !checkIn || !checkOut) return;
    setLoading(true);
    fetchAvailability(roomTypeId, checkIn, checkOut)
      .then((data) => setAvailability(data.results || data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [roomTypeId, checkIn, checkOut]);

  return { availability, loading };
};

// ─── useMyBookings ────────────────────────────────────────
export const useMyBookings = () => {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchMyBookings();
      setBookings(data.results || data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return { bookings, loading, error, refetch: load };
};
