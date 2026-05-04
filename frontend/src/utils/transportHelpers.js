// ─── Node Type Meta ───────────────────────────────────────
export const NODE_TYPE_META = {
  bus:   { label: 'Bus Stand',      icon: '🚌', color: '#16a34a', markerColor: '#16a34a' },
  auto:  { label: 'Auto Stand',     icon: '🛺', color: '#d97706', markerColor: '#d97706' },
  metro: { label: 'Metro Station',  icon: '🚇', color: '#7c3aed', markerColor: '#7c3aed' },
  taxi:  { label: 'Taxi Stand',     icon: '🚕', color: '#dc2626', markerColor: '#dc2626' },
};

export const getNodeTypeMeta = (type) =>
  NODE_TYPE_META[type] || { label: type, icon: '📍', color: '#6b7280', markerColor: '#6b7280' };

export const ALL_NODE_TYPES = ['all', 'bus', 'auto', 'metro', 'taxi'];

// ─── Filter ───────────────────────────────────────────────
export const filterNodes = (nodes, { search, type, city }) => {
  return nodes.filter((n) => {
    const matchSearch = !search ||
      n.name.toLowerCase().includes(search.toLowerCase()) ||
      (n.address || '').toLowerCase().includes(search.toLowerCase());
    const matchType = !type || type === 'all' || n.node_type === type;
    const matchCity = !city || n.city.toLowerCase().includes(city.toLowerCase());
    return matchSearch && matchType && matchCity;
  });
};

// ─── Coordinate Helpers ───────────────────────────────────
export const parseLocation = (locationField) => {
  // Django GIS returns { type: 'Point', coordinates: [lon, lat] }
  if (!locationField) return null;
  if (locationField.coordinates) {
    const [lon, lat] = locationField.coordinates;
    return [lat, lon]; // Leaflet expects [lat, lon]
  }
  return null;
};

export const haversineDistance = (lat1, lon1, lat2, lon2) => {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
    Math.cos((lat2 * Math.PI) / 180) *
    Math.sin(dLon / 2) ** 2;
  return (R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))).toFixed(1);
};
