import { useState } from 'react';
import { artFor, artworkDataUri } from '../utils/placeArt';
import './PlaceImage.css';

/**
 * The image contract for the whole app: a card never renders blank.
 *
 * OpenStreetMap carries no photographs, and the places this app is built for --
 * a roadside dhaba, a homestay in a small town, an auto stand -- are exactly
 * the ones with no image on Wikipedia either. So every place resolves to one of
 * three tiers:
 *
 *   1. a real internet photo  (image_url from OpenTripMap / Wikipedia / OSM tag)
 *   2. any secondary source the caller supplies, e.g. the OSM `image` tag
 *   3. generated category artwork, inline as an SVG data URI
 *
 * Tier 3 is a pure function of the name and category, so it can never 404 and
 * needs no network. That is what makes the guarantee hold rather than merely
 * being likely.
 *
 * `fallbackSrc` is normally itself a real photograph -- a bundled per-category
 * one -- so tier 3 is only reached for data that has no photograph and no
 * bundled category image either. When a supplied `fallbackSrc` is the image
 * actually on screen, `fallbackCredit` is shown next to it: a CC BY or CC BY-SA
 * photograph requires attribution, and the credit has to travel with the image
 * it applies to rather than sitting in a separate page.
 */
export default function PlaceImage({
  src,
  fallbackSrc,
  alt,
  category,
  name,
  className = '',
  badge,
  aspect = '4 / 3',
  fallbackCredit = '',
  onClick,
}) {
  const art = artFor(category, name);
  // Real photo first, then any secondary source, then generated artwork.
  const candidates = [src, fallbackSrc].filter((u) => typeof u === 'string' && u.trim());
  const [index, setIndex] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);

  const usingArtwork = index >= candidates.length;
  const current = usingArtwork ? artworkDataUri(art, name) : candidates[index];
  // Only credit the fallback when the fallback is what is actually shown. On a
  // card with its own photograph the bundled category image is never rendered,
  // and crediting a picture the visitor cannot see would be noise.
  const showingFallback = !usingArtwork && !failed && index === candidates.length - 1 && candidates.length > 1;

  const handleError = () => {
    // A real photo that 404s must not leave a hole: step to the next candidate,
    // and finally to artwork.
    if (index < candidates.length - 1) {
      setIndex((i) => i + 1);
      setLoaded(false);
      return;
    }
    setFailed(true);
  };

  return (
    <div
      className={`place-image ${className}`.trim()}
      style={{ aspectRatio: aspect }}
      onClick={onClick}
    >
      {!loaded && !failed && <div className="place-image__shimmer" aria-hidden="true" />}
      {failed ? (
        <div
          className="place-image__art"
          style={{ background: `linear-gradient(135deg, ${art.from}, ${art.to})` }}
        >
          <span className="place-image__glyph">{art.glyph}</span>
        </div>
      ) : (
        <img
          src={current}
          alt={alt || name || 'Place photo'}
          loading="lazy"
          decoding="async"
          onLoad={() => setLoaded(true)}
          onError={handleError}
          className={`place-image__img ${loaded ? 'is-loaded' : ''} ${
            usingArtwork ? 'is-artwork' : ''
          }`}
        />
      )}
      {badge ? <span className="place-image__badge">{badge}</span> : null}
      {showingFallback && fallbackCredit ? (
        <span className="place-image__credit" title={fallbackCredit}>
          {fallbackCredit}
        </span>
      ) : null}
      {usingArtwork && !failed ? (
        <span className="place-image__credit">no photo yet</span>
      ) : null}
    </div>
  );
}
