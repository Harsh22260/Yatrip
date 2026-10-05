import { asList, request } from './api';

// The food app is mounted at /api/ and its router registers the resource under
// 'food', so the paths are /api/food/. This used to hand-roll `fetch` against a
// hard-coded "http://localhost:8000/api", which meant no `credentials: 'include'`
// (so the SPA was anonymous on a cross-origin API even when signed in), no CSRF
// header on writes, and error messages that bypassed ApiError.
const FOOD = 'food';

const withQuery = (path, params) => {
  const search = new URLSearchParams();
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.set(key, value);
  });
  const query = search.toString();
  return query ? `${path}?${query}` : path;
};

// ─── Public reads ────────────────────────────────────────────────────
export const fetchFoodPlaces = async (filters = {}, location = null) =>
  request(
    withQuery(`${FOOD}/`, {
      lat: location?.lat,
      lon: location?.lon,
      category: filters.category !== 'all' ? filters.category : '',
      cuisine: filters.cuisine,
      search: filters.search,
      location_search: filters.locationSearch,
      is_veg: filters.isVeg,
      delivery: filters.delivery === 'true' ? 'true' : '',
      min_rating: filters.minRating,
      price_level: filters.priceLevel,
      sort_by: filters.sortBy,
      radius: filters.radius,
      page: filters.page || 1,
      page_size: filters.pageSize || 20,
    })
  );

export const fetchFoodPlaceById = async (id, options = {}) =>
  request(`${FOOD}/${id}/`, { signal: options.signal });

export const fetchNearbyFood = async ({ lat, lon, radius = 10, category = 'all' } = {}) =>
  request(
    withQuery(`${FOOD}/nearby/`, {
      lat,
      lon,
      radius,
      category: category !== 'all' ? category : '',
    })
  );

export const fetchFoodCategories = async () => asList(await request(`${FOOD}/categories/`));
export const fetchFoodCuisines = async () => asList(await request(`${FOOD}/cuisines/`));
export const fetchRandomFood = async (count = 20) =>
  request(withQuery(`${FOOD}/random/`, { count }));

// ─── Menu ────────────────────────────────────────────────────────────
export const fetchMenuItems = async (placeId) => asList(await request(`${FOOD}/${placeId}/menu-items/`));

export const createMenuItem = async (placeId, payload) =>
  request(`${FOOD}/${placeId}/menu-items/`, { method: 'POST', body: payload });

export const deleteMenuItem = async (placeId, itemId) =>
  request(`${FOOD}/${placeId}/menu-items/${itemId}/`, { method: 'DELETE' });

// ─── Business: my outlets ───────────────────────────────────────────
export const fetchMyFoodPlaces = async () =>
  asList(await request(withQuery(`${FOOD}/`, { mine: 'true', page_size: 100 })));

export const createFoodPlace = async (payload) =>
  request(FOOD, { method: 'POST', body: payload });

export const updateFoodPlace = async (id, payload) =>
  request(`${FOOD}/${id}/`, { method: 'PATCH', body: payload });

export const deleteFoodPlace = async (id) => request(`${FOOD}/${id}/`, { method: 'DELETE' });

// ─── OSM import ──────────────────────────────────────────────────────
/**
 * These are the only routes that hit Overpass, so they are rate limited and
 * never run automatically: a thin area used to trigger a blocking fetch inside
 * the browse request, which is a multi-second upstream call the traveller waits
 * through. Call these deliberately, or let the UI offer the button.
 */
export const importArea = async ({ lat, lon, radius = 8 } = {}) =>
  request(`${FOOD}/import-area/`, { method: 'POST', body: { lat, lon, radius } });

export const importCity = async (query) =>
  request(`${FOOD}/import-city/`, { method: 'POST', body: { q: query } });