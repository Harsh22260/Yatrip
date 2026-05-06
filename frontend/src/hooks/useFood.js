import { useState, useEffect, useCallback, useRef } from "react";
import foodService from "../services/foodService";
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
  const debounceRef = useRef(null);

  const fetchFoods = useCallback(async (f, loc) => {
    setLoading(true); setError(null);
    try {
      const data = await foodService.getAll(f, loc);
      setFoods(data.results || []);
      setTotal(data.total || 0);
      setTotalPages(data.total_pages || 0);
    } catch (err) {
      setError(err.message || "Failed to load food places.");
      setFoods([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch categories silently
  useEffect(() => {
    foodService.getCategories()
      .then(setCategories)
      .catch(() => setCategories([])); // silent fail
  }, []);

  useEffect(() => { fetchFoods(filters, userLocation); }, [filters, userLocation, fetchFoods]);

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
  const retry = useCallback(() => fetchFoods(filters, userLocation), [filters, userLocation, fetchFoods]);

  return {
    foods, total, totalPages, categories,
    loading, error, filters,
    userLocation, locationStatus,
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

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    foodService.getById(id)
      .then(setVendor)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  return { vendor, loading, error };
}