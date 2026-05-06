import { useState, useEffect, useCallback, useRef } from "react";
import attractionService from "../services/attractionService";
import { DEFAULT_FILTERS } from "../utils/attractionHelpers";

export default function useAttractions() {
  const [attractions, setAttractions]   = useState([]);
  const [total, setTotal]               = useState(0);
  const [totalPages, setTotalPages]     = useState(0);
  const [loading, setLoading]           = useState(false);
  const [error, setError]               = useState(null);
  const [userLocation, setUserLocation] = useState(null);
  const [locationStatus, setLocationStatus] = useState("idle"); // idle | requesting | granted | denied
  const [filters, setFilters]           = useState(DEFAULT_FILTERS);
  const [categories, setCategories]     = useState([]);

  const debounceTimer = useRef(null);

  // ── Fetch attractions ─────────────────────────────────────────────────────
  const fetchAttractions = useCallback(async (f, loc) => {
    setLoading(true);
    setError(null);
    try {
      const data = await attractionService.getAttractions(f, loc);
      setAttractions(data.results || []);
      setTotal(data.total || 0);
      setTotalPages(data.total_pages || 0);
    } catch (err) {
      setError(err.message || "Failed to load attractions.");
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Fetch categories ──────────────────────────────────────────────────────
  const fetchCategories = useCallback(async () => {
    try {
      const data = await attractionService.getCategories();
      setCategories(data);
    } catch {
      // silent fail — use static list from helpers
    }
  }, []);

  // ── Auto-refetch on filter / location change ──────────────────────────────
  useEffect(() => {
    fetchAttractions(filters, userLocation);
  }, [filters, userLocation, fetchAttractions]);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  // ── Location ──────────────────────────────────────────────────────────────
  const requestLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setLocationStatus("denied");
      return;
    }
    setLocationStatus("requesting");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const loc = { lat: pos.coords.latitude, lon: pos.coords.longitude };
        setUserLocation(loc);
        setLocationStatus("granted");
        setFilters((f) => ({ ...f, sortBy: "distance", page: 1 }));
      },
      () => {
        setLocationStatus("denied");
      },
      { timeout: 10000 }
    );
  }, []);

  const clearLocation = useCallback(() => {
    setUserLocation(null);
    setLocationStatus("idle");
    setFilters((f) => ({ ...f, sortBy: "rating", page: 1 }));
  }, []);

  // ── Filter helpers ────────────────────────────────────────────────────────
  const setFilter = useCallback((key, value) => {
    setFilters((f) => ({ ...f, [key]: value, page: 1 }));
  }, []);

  const setDebouncedFilter = useCallback((key, value, delay = 500) => {
    clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => {
      setFilters((f) => ({ ...f, [key]: value, page: 1 }));
    }, delay);
  }, []);

  const resetFilters = useCallback(() => {
    setFilters({
      ...DEFAULT_FILTERS,
      sortBy: userLocation ? "distance" : "rating",
    });
  }, [userLocation]);

  const setPage = useCallback((page) => {
    setFilters((f) => ({ ...f, page }));
  }, []);

  const setCategory = useCallback((category) => {
    setFilters((f) => ({ ...f, category, page: 1 }));
  }, []);

  const retry = useCallback(() => {
    fetchAttractions(filters, userLocation);
  }, [filters, userLocation, fetchAttractions]);

  return {
    // Data
    attractions,
    total,
    totalPages,
    categories,

    // UI State
    loading,
    error,
    filters,

    // Location
    userLocation,
    locationStatus,
    requestLocation,
    clearLocation,

    // Filter actions
    setFilter,
    setDebouncedFilter,
    resetFilters,
    setPage,
    setCategory,
    retry,
  };
}