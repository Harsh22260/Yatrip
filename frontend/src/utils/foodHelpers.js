export const FOOD_CATEGORIES = [
  { key: "all",        icon: "🍴", label: "All" },
  { key: "street_food",icon: "🥘", label: "Street Food" },
  { key: "restaurant", icon: "🍽️", label: "Restaurant" },
  { key: "cafe",       icon: "☕", label: "Café" },
  { key: "dhaba",      icon: "🍛", label: "Dhaba" },
  { key: "bakery",     icon: "🥐", label: "Bakery" },
  { key: "sweet_shop", icon: "🍬", label: "Sweet Shop" },
  { key: "juice_bar",  icon: "🥤", label: "Juice Bar" },
  { key: "fast_food",  icon: "🍔", label: "Fast Food" },
  { key: "other",      icon: "🍴", label: "Other" },
];

export const SORT_OPTIONS = [
  { value: "distance", label: "📍 Nearest" },
  { value: "rating",   label: "⭐ Top Rated" },
  { value: "name",     label: "🔤 A–Z" },
];

export const PRICE_OPTIONS = [
  { value: "",  label: "Any Price" },
  { value: "1", label: "₹ Budget" },
  { value: "2", label: "₹₹ Mid" },
  { value: "3", label: "₹₹₹ Fine" },
  { value: "4", label: "₹₹₹₹ Luxury" },
];

export const DEFAULT_FOOD_FILTERS = {
  category: "all", cuisine: "", search: "", locationSearch: "",
  isVeg: "", delivery: "", minRating: "", priceLevel: "",
  sortBy: "rating", page: 1, pageSize: 20,
};

export const getCategoryInfo = (key) =>
  FOOD_CATEGORIES.find(c => c.key === key) || FOOD_CATEGORIES[FOOD_CATEGORIES.length - 1];

export const formatDistance = (km) => {
  if (km == null) return null;
  if (km < 1)   return `${Math.round(km * 1000)}m`;
  if (km < 10)  return `${km.toFixed(1)} km`;
  return `${Math.round(km)} km`;
};

export const buildStars = (r = 0) =>
  "★".repeat(Math.round(r)) + "☆".repeat(5 - Math.round(r));

export const vegLabel = (isVeg) => {
  if (isVeg === true)  return { label: "🟢 Pure Veg", cls: "veg" };
  if (isVeg === false) return { label: "🔴 Non-Veg",  cls: "nonveg" };
  return { label: "🟡 Veg & Non-Veg", cls: "both" };
};
export const formatPrice = (priceLevel) => {
  if (!priceLevel) return "N/A";

  const map = {
    1: "₹",
    2: "₹₹",
    3: "₹₹₹",
    4: "₹₹₹₹"
  };

  return map[priceLevel] || "N/A";
};

export const osmLink = (lat, lon) =>
  `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}&zoom=17`;

/**
 * Returns metadata for a vendor type/category.
 * Matches backend FoodCategory choices.
 */
export const getVendorTypeMeta = (type) => {
  const map = {
    street_food: { icon: "🥘", label: "Street Food", color: "#f59e0b" },
    restaurant:  { icon: "🍽️", label: "Restaurant",  color: "#ef4444" },
    cafe:        { icon: "☕", label: "Café",        color: "#8b5cf6" },
    dhaba:       { icon: "🍛", label: "Dhaba",       color: "#10b981" },
    bakery:      { icon: "🥐", label: "Bakery",      color: "#ec4899" },
    sweet_shop:  { icon: "🍬", label: "Sweet Shop",  color: "#f43f5e" },
    juice_bar:   { icon: "🥤", label: "Juice Bar",   color: "#22c55e" },
    fast_food:   { icon: "🍔", label: "Fast Food",   color: "#f97316" },
    other:       { icon: "🍴", label: "Other",       color: "#6b7280" },
  };
  return map[type] || map.other;
};

/**
 * Returns an object with counts for star rating display.
 */
export const renderStars = (rating) => {
  const full = Math.floor(rating || 0);
  const half = (rating || 0) - full >= 0.5;
  return {
    full,
    half,
    empty: Math.max(0, 5 - full - (half ? 1 : 0))
  };
};

/**
 * Returns price bucket metadata based on price level (1-4).
 */
export const getPriceBucket = (level) => {
  const map = {
    1: { label: "Budget",    color: "#22c55e" },
    2: { label: "Mid-Range", color: "#f59e0b" },
    3: { label: "Premium",   color: "#ef4444" },
    4: { label: "Luxury",    color: "#7c3aed" },
  };
  return map[level] || { label: "N/A", color: "#9ca3af" };
};