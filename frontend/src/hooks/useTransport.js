import { useState, useEffect, useCallback } from 'react';
import {
  fetchTransportNodes,
  fetchNearbyNodes,
  fetchOSRMRoute,
  geocodeAddress,
} from '../services/transportService';

// ─── useTransportNodes ────────────────────────────────────
export const useTransportNodes = () => {
  const [nodes, setNodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchTransportNodes();
      setNodes(data.results || data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  return { nodes, loading, error, refetch: load };
};

// ─── useNearbyNodes ───────────────────────────────────────
export const useNearbyNodes = () => {
  const [nodes, setNodes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [userLocation, setUserLocation] = useState(null);
  const [locationDenied, setLocationDenied] = useState(false);

  const fetchNearby = useCallback(async (lat, lon) => {
    setLoading(true);
    try {
      const data = await fetchNearbyNodes(lat, lon);
      setNodes(data.results || data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const getUserLocation = useCallback(() => {
    if (!navigator.geolocation) { setError('Geolocation not supported'); return; }
    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        setUserLocation([latitude, longitude]);
        fetchNearby(latitude, longitude);
      },
      () => { setLocationDenied(true); setLoading(false); }
    );
  }, [fetchNearby]);

  return { nodes, loading, error, userLocation, locationDenied, getUserLocation };
};

// ─── useRoute ─────────────────────────────────────────────
export const useRoute = () => {
  const [route, setRoute] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const getRoute = useCallback(async (startLat, startLon, endLat, endLon) => {
    setLoading(true);
    setError(null);
    setRoute(null);
    try {
      const data = await fetchOSRMRoute(startLat, startLon, endLat, endLon);
      const leg = data.routes?.[0];
      if (!leg) throw new Error('No route found');
      setRoute({
        geometry: leg.geometry,
        distance_km: (leg.distance / 1000).toFixed(1),
        duration_min: Math.round(leg.duration / 60),
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  return { route, loading, error, getRoute, clearRoute: () => setRoute(null) };
};

// ─── useGeocode ───────────────────────────────────────────
export const useGeocode = () => {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const search = useCallback(async (query) => {
    if (!query || query.length < 3) { setResults([]); return; }
    setLoading(true);
    try {
      const data = await geocodeAddress(query);
      setResults(data);
    } catch (_) {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  return { results, loading, search, clearResults: () => setResults([]) };
};
