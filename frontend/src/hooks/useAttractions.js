import { useState, useEffect, useCallback } from 'react';
import {
  fetchAttractions,
  fetchAttractionById,
  fetchNearbyAttractions,
  fetchAttractionsByCity,
} from '../services/attractionService';

// ─── useAttractions ───────────────────────────────────────
export const useAttractions = () => {
  const [attractions, setAttractions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAttractions();
      setAttractions(data.results || data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  return { attractions, loading, error, refetch: load };
};

// ─── useAttractionDetail ──────────────────────────────────
export const useAttractionDetail = (id) => {
  const [attraction, setAttraction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetchAttractionById(id)
      .then(setAttraction)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  return { attraction, loading, error };
};

// ─── useNearbyAttractions ─────────────────────────────────
export const useNearbyAttractions = () => {
  const [nearby, setNearby] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [locationDenied, setLocationDenied] = useState(false);

  useEffect(() => {
    if (!navigator.geolocation) {
      setError('Geolocation not supported');
      return;
    }
    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const data = await fetchNearbyAttractions(
            pos.coords.latitude,
            pos.coords.longitude
          );
          setNearby(data.results || data);
        } catch (e) {
          setError(e.message);
        } finally {
          setLoading(false);
        }
      },
      () => {
        setLocationDenied(true);
        setLoading(false);
      }
    );
  }, []);

  return { nearby, loading, error, locationDenied };
};

// ─── useAttractionsByCity ─────────────────────────────────
export const useAttractionsByCity = (city) => {
  const [attractions, setAttractions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!city) return;
    setLoading(true);
    fetchAttractionsByCity(city)
      .then((data) => setAttractions(data.results || data))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [city]);

  return { attractions, loading, error };
};
