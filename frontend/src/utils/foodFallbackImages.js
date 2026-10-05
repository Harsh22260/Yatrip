/**
 * Real photographs for food cards that have none.
 *
 * The data is the reason this file exists. Nearly every food row imported from
 * OpenStreetMap has an empty `image_url`: OSM carries no photographs, and the
 * places this app is built for -- a roadside dhaba, a bakery in a small town --
 * are exactly the ones with no photograph on Wikipedia either. A name lookup
 * against Wikimedia Commons measured against this database filled 0 of the first
 * 30 rows, and the handful it did match earlier were wrong photographs (a Cape
 * Town shopping mall under "Blue Tokai, Delhi").
 *
 * So for most of this data there is no per-place photograph to be had. The choice
 * is then between a real photograph of that kind of place and generated artwork,
 * and the requirement is a real image. These nine photographs are bundled in
 * `public/food-fallback/`, which means:
 *
 *   - they are actual JPEG photographs, not SVG placeholders
 *   - they ship with the app, so a card never waits on the network or 404s
 *   - they are per category, so a bakery card shows bread and a dhaba card shows a
 *     highway dhaba, rather than one generic plate for every row
 *
 * Priority order for a card is: the place's own photo, then this category
 * photograph. An owner who registers an outlet and supplies a photo replaces the
 * category image for that row only.
 *
 * Every file is a Wikimedia Commons photograph. CC BY and CC BY-SA require
 * attribution, so the author and licence travel with each image: the credit is
 * rendered on the card, and the full list with links is in the site footer. CC0
 * files are credited too, as a courtesy rather than an obligation.
 */

const BASE = '/food-fallback';

export const FOOD_CATEGORY_FALLBACKS = {
  restaurant: {
    src: `${BASE}/restaurant.jpg`,
    author: 'Contrapunctus-1',
    licence: 'CC BY-SA 4.0',
    source: 'Interior of Agasi, Lajpat Nagar, Delhi',
    commonsPage:
      'https://commons.wikimedia.org/wiki/File:Interior_of_Agasi,_Lajpat_Nagar,_Delhi_(2025-10-04)_(1).jpg',
  },
  fast_food: {
    src: `${BASE}/fast_food.jpg`,
    author: 'Sergey A. Demidov',
    licence: 'CC BY 4.0',
    source: 'Vasilki burger',
    commonsPage:
      'https://commons.wikimedia.org/wiki/File:20260916_Minsk_Vasilki_Burger.jpg',
  },
  cafe: {
    src: `${BASE}/cafe.jpg`,
    author: 'Daderot',
    licence: 'CC0',
    source: 'Coffee shop, Wellington',
    commonsPage:
      'https://commons.wikimedia.org/wiki/File:Coffee_shop_2_-_Wellington,_New_Zealand.jpg',
  },
  dhaba: {
    src: `${BASE}/dhaba.jpg`,
    author: 'Kailash Mohankar',
    licence: 'CC BY 3.0',
    source: 'Bandar Wala Dhaba, Betul Highway',
    commonsPage:
      'https://commons.wikimedia.org/wiki/File:Bandar_Wala_Dhaba_on_Betul_Highway_-_panoramio.jpg',
  },
  bakery: {
    src: `${BASE}/bakery.jpg`,
    author: 'Clark Young',
    licence: 'CC0',
    source: 'Loaves of bread',
    commonsPage:
      'https://commons.wikimedia.org/wiki/File:Loaves_of_Bread_(Unsplash).jpg',
  },
  sweet_shop: {
    src: `${BASE}/sweet_shop.jpg`,
    author: 'Dipanker Dutta',
    licence: 'CC BY 2.0',
    source: 'Indian sweets display, Kolkata',
    commonsPage:
      'https://commons.wikimedia.org/wiki/File:Display_of_Indian_Sweets_Mithai_in_Kolkata,_West_Bengal.jpg',
  },
  juice_bar: {
    src: `${BASE}/juice_bar.jpg`,
    author: 'Joe Goldberg',
    licence: 'CC BY 2.0',
    source: 'Fruit juice stand',
    commonsPage:
      'https://commons.wikimedia.org/wiki/File:Fruit_juice_stand_(4080338565).jpg',
  },
  street_food: {
    src: `${BASE}/street_food.jpg`,
    author: 'Dudva',
    licence: 'CC0',
    source: 'Food vendor, Jaipur',
    commonsPage:
      'https://commons.wikimedia.org/wiki/File:Food_vendor_in_Jaipur.jpg',
  },
  other: {
    src: `${BASE}/other.jpg`,
    author: 'Nishant113',
    licence: 'CC BY-SA 4.0',
    source: 'Indian food thali',
    commonsPage:
      'https://commons.wikimedia.org/wiki/File:Indian_food_thali.jpg',
  },
};

/** Last-resort photograph for a category with no entry above. */
const GENERIC = FOOD_CATEGORY_FALLBACKS.other;

export function categoryFallback(category) {
  return FOOD_CATEGORY_FALLBACKS[category] || GENERIC;
}

/** One line, e.g. "Contrapunctus-1 · CC BY-SA 4.0 · Wikimedia Commons". */
export function fallbackCredit(category) {
  const photo = categoryFallback(category);
  return `${photo.author} · ${photo.licence} · Wikimedia Commons`;
}

/** Every bundled photograph, for the credits list in the footer. */
export function allFallbackCredits() {
  return Object.entries(FOOD_CATEGORY_FALLBACKS).map(([category, photo]) => ({
    category,
    ...photo,
  }));
}