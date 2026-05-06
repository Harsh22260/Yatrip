const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

const handleResponse = async (res) => {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.error || `HTTP ${res.status}`);
  }
  return res.json();
};

const attractionService = {
  // GET /api/attractions/ with all filters
  getAttractions: async (filters = {}, userLocation = null) => {
    const params = new URLSearchParams();
    if (userLocation?.lat) params.set("lat", userLocation.lat);
    if (userLocation?.lon) params.set("lon", userLocation.lon);
    if (filters.category && filters.category !== "all") params.set("category", filters.category);
    if (filters.search)          params.set("search", filters.search);
    if (filters.locationSearch)  params.set("location_search", filters.locationSearch);
    if (filters.minRating)       params.set("min_rating", filters.minRating);
    if (filters.isFree !== "")   params.set("is_free", filters.isFree);
    if (filters.sortBy)          params.set("sort_by", filters.sortBy);
    params.set("page",      filters.page || 1);
    params.set("page_size", filters.pageSize || 20);

    const res = await fetch(`${API_BASE}/attractions/?${params}`);
    return handleResponse(res);
  },

  // GET /api/attractions/:id/
  getAttractionById: async (id) => {
    const res = await fetch(`${API_BASE}/attractions/${id}/`);
    return handleResponse(res);
  },

  // GET /api/attractions/nearby/
  getNearby: async (lat, lon, radius = 400, category = "all") => {
    const params = new URLSearchParams({ lat, lon, radius });
    if (category !== "all") params.set("category", category);
    const res = await fetch(`${API_BASE}/attractions/nearby/?${params}`);
    return handleResponse(res);
  },

  // GET /api/attractions/categories/
  getCategories: async () => {
    const res = await fetch(`${API_BASE}/attractions/categories/`);
    return handleResponse(res);
  },

  // GET /api/attractions/random/
  getRandom: async (count = 20, category = "all") => {
    const params = new URLSearchParams({ count });
    if (category !== "all") params.set("category", category);
    const res = await fetch(`${API_BASE}/attractions/random/?${params}`);
    return handleResponse(res);
  },
};

export default attractionService;