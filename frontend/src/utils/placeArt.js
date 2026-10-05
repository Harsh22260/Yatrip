/**
 * Category artwork for PlaceImage.
 *
 * Kept out of the component file on purpose: PlaceImage.jsx is a component
 * module, and exporting plain helpers from it breaks React Fast Refresh.
 */

// Per-category artwork: two-stop gradient plus a glyph. Chosen so the categories
// stay visually distinct at card size.
export const CATEGORY_ART = {
  food: { from: '#ff9a3c', to: '#ff5f6d', glyph: '🍽️' },
  restaurant: { from: '#ff8f4c', to: '#e63946', glyph: '🍛' },
  cafe: { from: '#c98a5b', to: '#7b4b2a', glyph: '☕' },
  bakery: { from: '#f6c177', to: '#c2703a', glyph: '🥐' },
  hotel: { from: '#5b8def', to: '#3154d8', glyph: '🏨' },
  homestay: { from: '#8bc34a', to: '#4a7c2f', glyph: '🏡' },
  rental: { from: '#26a69a', to: '#00796b', glyph: '🏠' },
  attraction: { from: '#ab47bc', to: '#6a1b9a', glyph: '🏛️' },
  museum: { from: '#ec407a', to: '#ad1457', glyph: '🖼️' },
  nature: { from: '#66bb6a', to: '#1b5e20', glyph: '🌳' },
  temple: { from: '#ffa726', to: '#e65100', glyph: '🕉️' },
  park: { from: '#66bb6a', to: '#2e7d32', glyph: '🌳' },
  bus: { from: '#42a5f5', to: '#1565c0', glyph: '🚌' },
  auto: { from: '#ffca28', to: '#f57f17', glyph: '🛺' },
  metro: { from: '#7e57c2', to: '#4527a0', glyph: '🚇' },
  rail: { from: '#78909c', to: '#37474f', glyph: '🚆' },
  airport: { from: '#90a4ae', to: '#455a64', glyph: '✈️' },
  taxi: { from: '#ffb74d', to: '#f57c00', glyph: '🚕' },
  ferry: { from: '#4dd0e1', to: '#00838f', glyph: '⛴️' },
  other: { from: '#90a4ae', to: '#546e7a', glyph: '📍' },
};

const DEFAULT_ART_KEY = 'other';

/** Pick artwork for a place, falling back to a stable hash of its name. */
export function artFor(category, name = '') {
  if (category && CATEGORY_ART[category]) return CATEGORY_ART[category];

  // OSM amenity/shop values ("fast_food", "dhaba", "hotel") are not our keys.
  const blob = String(category || '').toLowerCase();
  if (blob.includes('food') || blob.includes('restaurant') || blob.includes('cafe')) {
    return CATEGORY_ART.food;
  }
  if (blob.includes('bar') || blob.includes('pub')) return CATEGORY_ART.cafe;
  if (blob.includes('hotel') || blob.includes('guest_house')) return CATEGORY_ART.hotel;
  if (blob.includes('attraction') || blob.includes('memorial')) return CATEGORY_ART.attraction;
  if (blob.includes('bus')) return CATEGORY_ART.bus;
  if (blob.includes('rail') || blob.includes('train')) return CATEGORY_ART.rail;
  if (blob.includes('metro') || blob.includes('subway')) return CATEGORY_ART.metro;
  if (blob.includes('airport') || blob.includes('aeroway')) return CATEGORY_ART.airport;
  if (blob.includes('taxi')) return CATEGORY_ART.taxi;

  // Deterministic pick so two unnamed bus stops do not look identical.
  const keys = Object.keys(CATEGORY_ART);
  let hash = 0;
  for (let i = 0; i < name.length; i += 1) {
    hash = (hash * 31 + name.charCodeAt(i)) % 100000;
  }
  return CATEGORY_ART[keys[hash % keys.length]] ?? CATEGORY_ART[DEFAULT_ART_KEY];
}

/**
 * Inline SVG artwork as a data URI, so it costs no request and cannot fail.
 * That is what lets the parent treat "artwork" as a real image source rather
 * than a separate empty-state branch.
 */
export function artworkDataUri(art, label) {
  const safe = String(label || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .slice(0, 28);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="400" viewBox="0 0 640 400">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="${art.from}"/><stop offset="100%" stop-color="${art.to}"/>
</linearGradient></defs>
<rect width="640" height="400" fill="url(#g)"/>
<text x="320" y="228" font-size="132" text-anchor="middle">${art.glyph}</text>
<text x="320" y="318" font-family="system-ui,sans-serif" font-size="30" font-weight="600"
 fill="rgba(255,255,255,.94)" text-anchor="middle">${safe}</text>
</svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}
