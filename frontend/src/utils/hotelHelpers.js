// ─── Date Helpers ─────────────────────────────────────────
export const formatDate = (dateStr) => {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
  });
};

export const toISODate = (date) => {
  if (!date) return '';
  const d = new Date(date);
  return d.toISOString().split('T')[0];
};

export const calcNights = (checkIn, checkOut) => {
  if (!checkIn || !checkOut) return 0;
  const diff = new Date(checkOut) - new Date(checkIn);
  return Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24)));
};

export const isDateInPast = (dateStr) => new Date(dateStr) < new Date();

// ─── Price Helpers ────────────────────────────────────────
export const formatPrice = (amount, currency = 'INR') =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency }).format(amount);

export const calcTotalPrice = (basePrice, nights, multiplier = 1, discountPct = 0) => {
  const raw = parseFloat(basePrice) * nights * parseFloat(multiplier);
  return raw * (1 - discountPct / 100);
};

// ─── Status Helpers ───────────────────────────────────────
export const STATUS_COLORS = {
  PENDING:   { bg: '#FFF3CD', text: '#856404', label: 'Pending Payment' },
  CONFIRMED: { bg: '#D1E7DD', text: '#0F5132', label: 'Confirmed' },
  CANCELLED: { bg: '#F8D7DA', text: '#842029', label: 'Cancelled' },
  EXPIRED:   { bg: '#E2E3E5', text: '#41464B', label: 'Expired' },
  HELD:      { bg: '#CFE2FF', text: '#084298', label: 'Hold (10 min)' },
};

export const getStatusInfo = (status) =>
  STATUS_COLORS[status] || { bg: '#eee', text: '#333', label: status };

// ─── Hold Timer Helper ────────────────────────────────────
export const getHoldSecondsLeft = (holdExpiresAt) => {
  if (!holdExpiresAt) return 0;
  const diff = new Date(holdExpiresAt) - new Date();
  return Math.max(0, Math.floor(diff / 1000));
};

// ─── Rating Helper ────────────────────────────────────────
export const renderStars = (rating) => {
  const full = Math.floor(rating);
  const half = rating - full >= 0.5;
  return { full, half, empty: 5 - full - (half ? 1 : 0) };
};
