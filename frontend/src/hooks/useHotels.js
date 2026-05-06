import { useState, useEffect, useCallback } from 'react';
import {
  fetchHotels,
  fetchHotelById,
  fetchRoomTypes,
  fetchRatePlans,
  fetchMyBookings,
  fetchMyHotels,
} from '../services/hotelService';

export const useHotels = () => {
  const [hotels, setHotels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchHotels();
      setHotels(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  return { hotels, loading, error, refetch: load };
};

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

export const useRoomTypes = (hotelId) => {
  const [roomTypes, setRoomTypes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!hotelId) return;
    setLoading(true);
    fetchRoomTypes(hotelId)
      .then(data => setRoomTypes(Array.isArray(data) ? data : []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [hotelId]);

  return { roomTypes, loading, error };
};

export const useRatePlans = (roomTypeId) => {
  const [ratePlans, setRatePlans] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!roomTypeId) return;
    setLoading(true);
    fetchRatePlans(roomTypeId)
      .then(data => setRatePlans(Array.isArray(data) ? data : []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [roomTypeId]);

  return { ratePlans, loading };
};

export const useMyBookings = () => {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchMyBookings();
      setBookings(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  return { bookings, loading, error, refetch: load };
};

// ─── Business Hook ─────────────────────────────────────────
export const useMyHotels = () => {
  const [hotels, setHotels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMyHotels();
      setHotels(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  return { hotels, loading, error, refetch: load };
};