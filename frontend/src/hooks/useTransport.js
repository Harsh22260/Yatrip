import { useState, useEffect, useCallback } from 'react';
import {
  fetchTransportNodes,
  fetchNearbyNodes,
  loadAreaTransport,
  waitForAreaImport,
  fetchOSRMRoute,
  geocodeAddress,
} from '../services/transportService';
import { useGeolocation } from './useGeolocation';

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

  // Initial fetch, guarded so a response arriving after unmount is discarded.
  // Written as an async body rather than calling `load()` because `load` flips
  // state synchronously, which the react-hooks lint rules reject inside an
  // effect. `refetch` still exposes the imperative version for the retry button.
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const data = await fetchTransportNodes();
        if (active) setNodes(data.results || data);
      } catch (e) {
        if (active) setError(e.message);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return { nodes, loading, error, refetch: load };
};

// ─── useNearbyNodes ───────────────────────────────────────
// The location request itself is delegated to useGeolocation so the failure
// reason is preserved. This hook keeps the "which nodes are near me" query.
export const useNearbyNodes = () => {
  const [nodes, setNodes] = useState([]);
  const [byType, setByType] = useState({});
  const [radiusKm, setRadiusKm] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [areaProgress, setAreaProgress] = useState('');
  const [loadingArea, setLoadingArea] = useState(false);
  const [areaResult, setAreaResult] = useState(null);

  const fetchNearby = useCallback(async (lat, lon, km = 10) => {
    setLoading(true);
    try {
      const data = await fetchNearbyNodes(lat, lon, km);
      setNodes(data.results || []);
      setByType(data.by_type || {});
      setRadiusKm(data.radius_km ?? km);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Leaflet takes [lat, lon, accuracy]; the fix already arrives as an object.
  const geo = useGeolocation({
    onFix: ({ lat, lon }) => {
      setError(null);
      fetchNearby(lat, lon);
    },
  });

  const userLocation = geo.coords
    ? [geo.coords.lat, geo.coords.lon, geo.accuracy ?? 60]
    : null;

  /** Import hubs for wherever the user is standing, on demand. */
  const loadCurrentArea = useCallback(
    async (km = 25) => {
      if (!geo.coords) return;
      setLoadingArea(true);
      setLoadError(null);
      setAreaProgress('');
      try {
        // Queues the import and returns straight away; the wait happens in
        // `waitForAreaImport`, which polls instead of holding one request open
        // for the several minutes a full Overpass sweep takes.
        const queued = await loadAreaTransport({
          lat: geo.coords.lat,
          lon: geo.coords.lon,
          radiusKm: km,
        });
        const final = await waitForAreaImport(queued.job_id, (state) => {
          setAreaResult((prev) => ({ ...prev, ...state }));
          setAreaProgress(state.message || '');
        });

        // Re-read the neighbourhood rather than trusting the queued response,
        // which no longer carries the node list now that the work is async.
        const fresh = await fetchNearbyNodes(geo.coords.lat, geo.coords.lon, km);
        setNodes(fresh.nodes || []);
        setByType(fresh.by_type || {});
        setRadiusKm(fresh.radius_km ?? km);
        setAreaResult((prev) => ({ ...prev, ...final }));
        setAreaProgress(final.message || '');
      } catch (e) {
        setLoadError(e.message);
      } finally {
        setLoadingArea(false);
      }
    },
    [geo.coords],
  );

  return {
    nodes,
    byType,
    radiusKm,
    loading: loading || geo.loading,
    error: error || geo.error,
    loadError,
    areaProgress,
    loadingArea,
    areaResult,
    loadCurrentArea,
    userLocation,
    locationDenied: geo.error?.code === 'denied',
    getUserLocation: geo.locate,
    geo,
  };
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
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  return { results, loading, search, clearResults: () => setResults([]) };
};
