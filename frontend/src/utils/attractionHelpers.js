// ─── Category Helpers ─────────────────────────────────────
export const CATEGORY_META = {
  monument: { label: 'Monument', icon: '🏛️', color: '#8B5CF6' },
  temple:   { label: 'Temple',   icon: '🛕', color: '#F59E0B' },
  park:     { label: 'Park',     icon: '🌿', color: '#10B981' },
  museum:   { label: 'Museum',   icon: '🖼️', color: '#3B82F6' },
  nature:   { label: 'Nature',   icon: '🏔️', color: '#06B6D4' },
  other:    { label: 'Other',    icon: '📍', color: '#6B7280' },
};

export const getCategoryMeta = (category) =>
  CATEGORY_META[category] || CATEGORY_META.other;

// ─── Time Helpers ─────────────────────────────────────────
export const formatTime = (timeStr) => {
  if (!timeStr) return null;
  const [h, m] = timeStr.split(':');
  const hour = parseInt(h);
  const ampm = hour >= 12 ? 'PM' : 'AM';
  const hour12 = hour % 12 || 12;
  return `${hour12}:${m} ${ampm}`;
};

export const isOpenNow = (openingTime, closingTime) => {
  if (!openingTime || !closingTime) return null;
  const now = new Date();
  const [oh, om] = openingTime.split(':').map(Number);
  const [ch, cm] = closingTime.split(':').map(Number);
  const currentMins = now.getHours() * 60 + now.getMinutes();
  const openMins = oh * 60 + om;
  const closeMins = ch * 60 + cm;
  return currentMins >= openMins && currentMins <= closeMins;
};

// ─── Price Helpers ────────────────────────────────────────
export const formatEntryFee = (fee) => {
  if (!fee || parseFloat(fee) === 0) return 'Free Entry';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR',
  }).format(fee);
};

// ─── Filter Helpers ───────────────────────────────────────
export const CATEGORIES = ['all', 'monument', 'temple', 'park', 'museum', 'nature', 'other'];

export const filterAttractions = (attractions, { search, category, city }) => {
  return attractions.filter((a) => {
    const matchSearch = !search ||
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.city.toLowerCase().includes(search.toLowerCase());
    const matchCategory = !category || category === 'all' || a.category === category;
    const matchCity = !city || a.city.toLowerCase().includes(city.toLowerCase());
    return matchSearch && matchCategory && matchCity;
  });
};
