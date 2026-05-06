import { useState, useEffect, useCallback } from 'react';
import {
  fetchRentals,
  fetchRentalById,
  fetchNearbyRentals,
  fetchAmenities,
} from '../services/rentalService';

// ─── useRentals ───────────────────────────────────────────
export const useRentals = () => {
  const [rentals, setRentals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRentals();
      const results = data.results || data;
      setRentals(Array.isArray(results) ? results : []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  return { rentals, loading, error, refetch: load };
};

// ─── useRentalDetail ──────────────────────────────────────
export const useRentalDetail = (id) => {
  const [rental, setRental] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetchRentalById(id)
      .then(setRental)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  return { rental, loading, error };
};

// ─── useNearbyRentals ─────────────────────────────────────
export const useNearbyRentals = () => {
  const [rentals, setRentals] = useState([]);
  const [loading, setLoading] = useState(false);
  const [locationDenied, setLocationDenied] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!navigator.geolocation) { setError('Geolocation not supported'); return; }
    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const data = await fetchNearbyRentals(pos.coords.latitude, pos.coords.longitude);
          const results = data.results || data;
          setRentals(Array.isArray(results) ? results : []);
        } catch (e) { setError(e.message); }
        finally { setLoading(false); }
      },
      () => { setLocationDenied(true); setLoading(false); }
    );
  }, []);

  return { rentals, loading, error, locationDenied };
};

// ─── useAmenities ─────────────────────────────────────────
export const useAmenities = () => {
  const [amenities, setAmenities] = useState([]);

  useEffect(() => {
    fetchAmenities()
      .then((data) => {
        const results = data.results || data;
        setAmenities(Array.isArray(results) ? results : []);
      })
      .catch(console.error);
  }, []);

  return { amenities };
};
