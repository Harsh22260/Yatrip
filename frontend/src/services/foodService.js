const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

const handle = async (res) => {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.error || `HTTP ${res.status}`);
  }
  return res.json();
};

const foodService = {
  getAll: async (filters = {}, location = null) => {
    const p = new URLSearchParams();
    if (location?.lat) p.set("lat", location.lat);
    if (location?.lon) p.set("lon", location.lon);
    if (filters.category && filters.category !== "all") p.set("category", filters.category);
    if (filters.cuisine)        p.set("cuisine", filters.cuisine);
    if (filters.search)         p.set("search", filters.search);
    if (filters.locationSearch) p.set("location_search", filters.locationSearch);
    if (filters.isVeg !== "")   p.set("is_veg", filters.isVeg);
    if (filters.delivery === "true") p.set("delivery", "true");
    if (filters.minRating)      p.set("min_rating", filters.minRating);
    if (filters.priceLevel)     p.set("price_level", filters.priceLevel);
    if (filters.sortBy)         p.set("sort_by", filters.sortBy);
    p.set("page",      filters.page || 1);
    p.set("page_size", filters.pageSize || 20);
    return handle(await fetch(`${API_BASE}/food/?${p}`));
  },

  getById:    async (id)   => handle(await fetch(`${API_BASE}/food/${id}/`)),
  getNearby:  async (lat, lon, radius = 10, category = "all") => {
    const p = new URLSearchParams({ lat, lon, radius });
    if (category !== "all") p.set("category", category);
    return handle(await fetch(`${API_BASE}/food/nearby/?${p}`));
  },
  getCategories: async () => handle(await fetch(`${API_BASE}/food/categories/`)),
  getCuisines:   async () => handle(await fetch(`${API_BASE}/food/cuisines/`)),
  getRandom:     async (count = 20) =>
    handle(await fetch(`${API_BASE}/food/random/?count=${count}`)),
};

export default foodService;