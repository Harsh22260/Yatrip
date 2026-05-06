export const CATEGORIES = [
  { key: "all",      icon: "🗺️",  label: "All" },
  { key: "monument", icon: "🏛️",  label: "Monument" },
  { key: "temple",   icon: "🛕",  label: "Temple" },
  { key: "park",     icon: "🌿",  label: "Park" },
  { key: "museum",   icon: "🖼️",  label: "Museum" },
  { key: "nature",   icon: "🏔️",  label: "Nature" },
  { key: "other",    icon: "📍",  label: "Other" },
];

export const SORT_OPTIONS = [
  { value: "distance", label: "📍 Nearest First" },
  { value: "rating",   label: "⭐ Top Rated" },
  { value: "name",     label: "🔤 A – Z" },
];

export const RATING_OPTIONS = [
  { value: "",    label: "Any Rating" },
  { value: "3",   label: "3+ ⭐" },
  { value: "4",   label: "4+ ⭐" },
  { value: "4.5", label: "4.5+ ⭐" },
];

export const FEE_OPTIONS = [
  { value: "",      label: "Any Entry" },
  { value: "true",  label: "🆓 Free Only" },
  { value: "false", label: "🎟️ Paid Only" },
];

export const DEFAULT_FILTERS = {
  category: "all",
  search: "",
  locationSearch: "",
  minRating: "",
  isFree: "",
  sortBy: "rating",
  page: 1,
  pageSize: 20,
};

// Format distance nicely
export const formatDistance = (km) => {
  if (km == null) return null;
  if (km < 1)   return `${Math.round(km * 1000)}m`;
  if (km < 10)  return `${km.toFixed(1)} km`;
  return `${Math.round(km)} km`;
};

// Get category object by key
export const getCategoryInfo = (key) =>
  CATEGORIES.find((c) => c.key === key) || CATEGORIES[CATEGORIES.length - 1];

// Build star string
export const buildStars = (rating = 0) => {
  const full  = Math.round(rating);
  const empty = 5 - full;
  return "★".repeat(Math.max(0, full)) + "☆".repeat(Math.max(0, empty));
};

// Format entry fee
export const formatFee = (attraction) => {
  if (attraction.is_free) return { label: "Free", type: "free" };
  if (attraction.entry_fee) return { label: `₹${attraction.entry_fee}`, type: "paid" };
  return { label: "Paid", type: "paid" };
};

// Build location string
export const formatLocation = (attraction, short = false) => {
  if (short) {
    return [attraction.city, attraction.state].filter(Boolean).join(", ");
  }
  return [attraction.address, attraction.city, attraction.state, attraction.country]
    .filter(Boolean)
    .join(", ");
};

// Haversine distance (client-side fallback)
export const haversineKm = (lat1, lon1, lat2, lon2) => {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
    Math.cos((lat2 * Math.PI) / 180) *
    Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.asin(Math.sqrt(a));
};

// OSM map link
export const osmMapLink = (lat, lon) =>
  `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}&zoom=16`;

// Google Maps link
export const googleMapsLink = (lat, lon, name) =>
  `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(name)}&query_place_id=${lat},${lon}`;