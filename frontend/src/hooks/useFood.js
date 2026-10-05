import { useState, useEffect, useCallback, useRef } from "react";
import {
  fetchFoodPlaces,
  fetchFoodPlaceById,
  fetchFoodCategories,
  importArea,
  importCity,
} from "../services/foodService";
import { DEFAULT_FOOD_FILTERS } from "../utils/foodHelpers";

export default function useFood() {
  const [foods, setFoods]           = useState([]);
  const [total, setTotal]           = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState(null);
  const [userLocation, setUserLocation] = useState(null);
  const [locationStatus, setLocationStatus] = useState("idle");
  const [filters, setFilters]       = useState(DEFAULT_FOOD_FILTERS);
  const [categories, setCategories] = useState([]);
  // True when the area has little or no coverage, so the list can offer to import
  // it rather than looking broken.
  const [sparse, setSparse]         = useState(false);
  const [importing, setImporting]   = useState(false);
  const [importMessage, setImportMessage] = useState("");
  const debounceRef = useRef(null);

  const fetchFoods = useCallback(async (f, loc, signal) => {
    // Flag lifecycle lives here here rather than in the effect body so every
    // caller (effect, retry, post-import refresh) gets it consistently.
    setLoading(true);
    setError(null);
    try {
      const data = await fetchFoodPlaces(f, loc);
      // A response that arrived after a newer request started is stale; drop it
      // rather than letting it overwrite the current results.
      if (signal?.aborted) return;
      setFoods(data.results || []);
      setTotal(data.total || 0);
      setTotalPages(data.total_pages || 0);
      setSparse(Boolean(data.sparse) || (data.total || 0) === 0);
    } catch (err) {
      if (signal?.aborted) return;
      setError(err.message || "Failed to load food places.");
      setFoods([]);
    } finally {
      // An aborted request is stale; it must not clear the flag for the newer
      // request that is still in flight.
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  // Fetch categories silently
  useEffect(() => {
    let active = true;
    fetchFoodCategories()
      .then((data) => { if (active) setCategories(data); })
      .catch(() => { if (active) setCategories([]); }); // silent fail
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    // Fetching on mount and on filter change is a subscription to a remote
    // collection, not derived state, so the rule about setState in an effect body
    // does not apply. The abort on cleanup is what keeps a slow earlier response
    // from overwriting a newer one.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchFoods(filters, userLocation, controller.signal);
    return () => controller.abort();
  }, [filters, userLocation, fetchFoods]);

  const requestLocation = useCallback(() => {
    if (!navigator.geolocation) { setLocationStatus("denied"); return; }
    setLocationStatus("requesting");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const loc = { lat: pos.coords.latitude, lon: pos.coords.longitude };
        setUserLocation(loc);
        setLocationStatus("granted");
        setFilters(f => ({ ...f, sortBy: "distance", page: 1 }));
      },
      () => setLocationStatus("denied"),
      { timeout: 10000 }
    );
  }, []);

  const clearLocation = useCallback(() => {
    setUserLocation(null);
    setLocationStatus("idle");
    setFilters(f => ({ ...f, sortBy: "rating", page: 1 }));
  }, []);

  const setFilter = useCallback((key, value) =>
    setFilters(f => ({ ...f, [key]: value, page: 1 })), []);

  const setDebouncedFilter = useCallback((key, value, delay = 500) => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() =>
      setFilters(f => ({ ...f, [key]: value, page: 1 })), delay);
  }, []);

  const resetFilters = useCallback(() =>
    setFilters({ ...DEFAULT_FOOD_FILTERS, sortBy: userLocation ? "distance" : "rating" }),
    [userLocation]);

  const setPage = useCallback((page) => setFilters(f => ({ ...f, page })), []);
  const setCategory = useCallback((category) => setFilters(f => ({ ...f, category, page: 1 })), []);
  const refresh = useCallback(() => fetchFoods(filters, userLocation), [filters, userLocation, fetchFoods]);

  const retry = refresh;

  /**
   * Pull food places for the current area into the database.
   *
   * Importing is opt-in on purpose: the browse endpoints only read the database
   * now, because a thin result used to fire a blocking Overpass request that the
   * traveller sat through on every poll.
   */
  const runImport = useCallback(async () => {
    setImporting(true);
    setImportMessage("");
    try {
      const radius = filters.radius || (userLocation ? 10 : 8);
      const res = userLocation
        ? await importArea({ lat: userLocation.lat, lon: userLocation.lon, radius })
        : await importCity(filters.locationSearch || "");
      const saved = res?.saved ?? 0;
      setImportMessage(
        res?.status === "pending"
          ? "An import for this area is already running. Try again in a moment."
          : saved
            ? `Added ${saved} place${saved === 1 ? "" : "s"} to this area.`
            : "No new places were found for this area."
      );
      if (saved) setFilters(f => ({ ...f, page: 1 }));
    } catch (err) {
      setImportMessage(err.message || "Import failed.");
    } finally {
      setImporting(false);
      // Give the write transaction a moment to land before re-reading.
      setTimeout(refresh, 400);
    }
  }, [filters, userLocation, refresh]);

  return {
    foods, total, totalPages, categories,
    loading, error, filters,
    userLocation, locationStatus,
    sparse, importing, importMessage, runImport,
    requestLocation, clearLocation,
    setFilter, setDebouncedFilter, resetFilters,
    setPage, setCategory, retry,
  };
}

/**
 * Hook to fetch a single vendor's detail by ID.
 */
export function useVendorDetail(id) {
  const [vendor, setVendor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // A detail fetch is re-run whenever the id changes, so the previous request has
  // to be cancelled or a slow earlier response can land on the newer page.
  const abortRef = useRef(null);

  const loadDetail = useCallback(async (targetId, signal) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchFoodPlaceById(targetId, { signal });
      if (!signal?.aborted) setVendor(data);
    } catch (err) {
      if (signal?.aborted || err?.name === "AbortError") return;
      setError(err.message);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!id) return undefined;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    // Remote read keyed on the route id, not derived state.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadDetail(id, controller.signal);
    return () => controller.abort();
  }, [id, loadDetail]);

  return { vendor, loading, error };
}