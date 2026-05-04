// ─── Rental Type Meta ─────────────────────────────────────
export const RENTAL_TYPE_META = {
  homestay: { label: 'Homestay', icon: '🏡', color: '#16a34a', bg: '#f0fdf4' },
  pg:       { label: 'Paying Guest', icon: '🏘️', color: '#9333ea', bg: '#faf5ff' },
  hostel:   { label: 'Hostel', icon: '🛏️', color: '#0891b2', bg: '#ecfeff' },
};

export const getRentalTypeMeta = (type) =>
  RENTAL_TYPE_META[type] || { label: type, icon: '🏠', color: '#6b7280', bg: '#f9fafb' };

export const ALL_RENTAL_TYPES = ['all', 'homestay', 'pg', 'hostel'];

// ─── Price Helpers ────────────────────────────────────────
export const formatMonthlyRent = (price) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(price);

export const getPriceTier = (price) => {
  const p = parseFloat(price);
  if (p <= 5000)  return { label: 'Budget', color: '#16a34a', dots: 1 };
  if (p <= 12000) return { label: 'Mid-range', color: '#d97706', dots: 2 };
  return { label: 'Premium', color: '#dc2626', dots: 3 };
};

// ─── Amenity Icons ────────────────────────────────────────
export const AMENITY_ICONS = {
  wifi: '📶', ac: '❄️', parking: '🅿️', laundry: '🧺',
  kitchen: '🍳', gym: '💪', tv: '📺', security: '🔒',
  meals: '🍱', hot_water: '🚿', balcony: '🌅', lift: '🛗',
};

export const getAmenityIcon = (name) =>
  AMENITY_ICONS[name.toLowerCase().replace(' ', '_')] || '✓';

// ─── Filter Helpers ───────────────────────────────────────
export const filterRentals = (rentals, { search, type, maxPrice, minRooms, amenities }) => {
  return rentals.filter((r) => {
    const matchSearch = !search ||
      r.name.toLowerCase().includes(search.toLowerCase()) ||
      r.address.toLowerCase().includes(search.toLowerCase());
    const matchType = !type || type === 'all' || r.rental_type === type;
    const matchPrice = !maxPrice || parseFloat(r.price_per_month) <= parseFloat(maxPrice);
    const matchRooms = !minRooms || r.available_rooms >= parseInt(minRooms);
    const matchAmenities = !amenities?.length ||
      amenities.every((a) => r.amenities?.some((ra) => ra.name.toLowerCase() === a.toLowerCase()));
    return matchSearch && matchType && matchPrice && matchRooms && matchAmenities;
  });
};
