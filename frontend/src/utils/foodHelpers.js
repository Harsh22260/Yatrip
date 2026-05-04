// ─── Vendor Type ──────────────────────────────────────────
export const VENDOR_TYPE_META = {
  registered: { label: 'Registered Vendor', icon: '🏪', color: '#0891b2' },
  street:     { label: 'Street Vendor',     icon: '🛺', color: '#d97706' },
};

export const getVendorTypeMeta = (type) =>
  VENDOR_TYPE_META[type] || VENDOR_TYPE_META.registered;

// ─── Price Helpers ────────────────────────────────────────
export const formatPrice = (amount) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(amount);

export const getPriceBucket = (cost) => {
  const c = parseFloat(cost);
  if (c <= 100) return { label: '₹ Budget', color: '#16a34a' };
  if (c <= 300) return { label: '₹₹ Mid-range', color: '#d97706' };
  return { label: '₹₹₹ Premium', color: '#dc2626' };
};

// ─── Rating Helpers ───────────────────────────────────────
export const renderStars = (rating) => {
  const full = Math.floor(rating);
  const half = rating - full >= 0.5;
  return { full, half, empty: 5 - full - (half ? 1 : 0) };
};

// ─── Filter Helpers ───────────────────────────────────────
export const filterVendors = (vendors, { search, type, category, maxCost }) => {
  return vendors.filter((v) => {
    const matchSearch = !search ||
      v.name.toLowerCase().includes(search.toLowerCase()) ||
      v.address.toLowerCase().includes(search.toLowerCase());
    const matchType = !type || type === 'all' || v.vendor_type === type;
    const matchCategory = !category || category === 'all' ||
      v.category === parseInt(category) || v.category_name === category;
    const matchCost = !maxCost || parseFloat(v.avg_cost) <= parseFloat(maxCost);
    return matchSearch && matchType && matchCategory && matchCost;
  });
};
