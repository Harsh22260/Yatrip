import { useState, useEffect, useCallback } from 'react';
import {
  fetchVendors,
  fetchVendorById,
  fetchNearbyVendors,
  fetchFoodCategories,
} from '../services/foodService';

// ─── useVendors ───────────────────────────────────────────
export const useVendors = () => {
  const [vendors, setVendors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchVendors();
      setVendors(data.results || data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  return { vendors, loading, error, refetch: load };
};

// ─── useVendorDetail ──────────────────────────────────────
export const useVendorDetail = (id) => {
  const [vendor, setVendor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetchVendorById(id)
      .then(setVendor)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  return { vendor, loading, error };
};

// ─── useNearbyVendors ─────────────────────────────────────
export const useNearbyVendors = () => {
  const [nearby, setNearby] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [locationDenied, setLocationDenied] = useState(false);

  useEffect(() => {
    if (!navigator.geolocation) { setError('Geolocation not supported'); return; }
    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const data = await fetchNearbyVendors(pos.coords.latitude, pos.coords.longitude);
          setNearby(data.results || data);
        } catch (e) { setError(e.message); }
        finally { setLoading(false); }
      },
      () => { setLocationDenied(true); setLoading(false); }
    );
  }, []);

  return { nearby, loading, error, locationDenied };
};

// ─── useFoodCategories ────────────────────────────────────
export const useFoodCategories = () => {
  const [categories, setCategories] = useState([]);

  useEffect(() => {
    fetchFoodCategories()
      .then((data) => setCategories(data.results || data))
      .catch(console.error);
  }, []);

  return { categories };
};
