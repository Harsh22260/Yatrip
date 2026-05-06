import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import attractionService from "../../services/attractionService";
import {
  getCategoryInfo,
  formatDistance,
  buildStars,
  formatFee,
  formatLocation,
  osmMapLink,
  googleMapsLink,
} from "../../utils/attractionHelpers";
import "./AttractionDetailPage.css";

const PLACEHOLDERS = {
  monument: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
  temple:   "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
  park:     "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)",
  museum:   "linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)",
  nature:   "linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)",
  other:    "linear-gradient(135deg, #fccb90 0%, #d57eeb 100%)",
};

export default function AttractionDetailPage() {
  const { id }   = useParams();
  const navigate = useNavigate();

  const [attraction, setAttraction] = useState(null);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState(null);

  useEffect(() => {
    setLoading(true);
    attractionService
      .getAttractionById(id)
      .then(setAttraction)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <DetailSkeleton />;
  if (error)   return <ErrorState error={error} onBack={() => navigate(-1)} />;
  if (!attraction) return null;

  const cat  = getCategoryInfo(attraction.category);
  const fee  = formatFee(attraction);
  const dist = formatDistance(attraction.distance_km);
  const fullLocation = formatLocation(attraction, false);

  return (
    <div className="adp">
      {/* ── BACK ── */}
      <button className="adp__back" onClick={() => navigate(-1)}>
        ← Back to Attractions
      </button>

      {/* ── HERO ── */}
      <div className="adp__hero">
        {attraction.image_url ? (
          <img className="adp__hero-img" src={attraction.image_url} alt={attraction.name} />
        ) : (
          <div
            className="adp__hero-placeholder"
            style={{ background: PLACEHOLDERS[attraction.category] || PLACEHOLDERS.other }}
          >
            <span>{cat.icon}</span>
          </div>
        )}
        <div className="adp__hero-overlay">
          <span className="adp__cat-badge">{cat.icon} {cat.label}</span>
          <h1 className="adp__name">{attraction.name}</h1>
          {fullLocation && (
            <p className="adp__location">📌 {fullLocation}</p>
          )}
        </div>
      </div>

      {/* ── MAIN CONTENT ── */}
      <div className="adp__body">

        {/* ── QUICK STATS ── */}
        <div className="adp__stats">
          <div className="adp__stat">
            <span className="adp__stat-icon">⭐</span>
            <div>
              <strong>{attraction.rating ? parseFloat(attraction.rating).toFixed(1) : "—"}</strong>
              <small>{attraction.review_count ? `${attraction.review_count} reviews` : "No reviews"}</small>
            </div>
          </div>
          <div className="adp__stat">
            <span className="adp__stat-icon">{fee.type === "free" ? "🆓" : "🎟️"}</span>
            <div>
              <strong>{fee.label}</strong>
              <small>Entry Fee</small>
            </div>
          </div>
          {dist && (
            <div className="adp__stat">
              <span className="adp__stat-icon">📏</span>
              <div>
                <strong>{dist}</strong>
                <small>From You</small>
              </div>
            </div>
          )}
          {attraction.opening_hours?.raw && (
            <div className="adp__stat">
              <span className="adp__stat-icon">🕐</span>
              <div>
                <strong>Open</strong>
                <small>{attraction.opening_hours.raw}</small>
              </div>
            </div>
          )}
        </div>

        {/* ── STARS ── */}
        <div className="adp__stars">
          <span className="adp__stars-text">{buildStars(attraction.rating)}</span>
          <span className="adp__stars-label">
            {attraction.rating
              ? `Rated ${parseFloat(attraction.rating).toFixed(1)} / 5`
              : "Not yet rated"}
          </span>
        </div>

        {/* ── DESCRIPTION ── */}
        {attraction.description && (
          <div className="adp__section">
            <h2>About</h2>
            <p>{attraction.description}</p>
          </div>
        )}

        {/* ── DETAILS CHIPS ── */}
        <div className="adp__section">
          <h2>Details</h2>
          <div className="adp__chips">
            <span className="adp__chip">🏷️ {cat.icon} {cat.label}</span>
            <span className={`adp__chip adp__chip--${fee.type}`}>{fee.type === "free" ? "🆓" : "🎟️"} {fee.label}</span>
            {attraction.country && <span className="adp__chip">🌍 {attraction.country}</span>}
            {attraction.state   && <span className="adp__chip">📍 {attraction.state}</span>}
            {attraction.city    && <span className="adp__chip">🏙️ {attraction.city}</span>}
            {attraction.phone   && (
              <a className="adp__chip adp__chip--link" href={`tel:${attraction.phone}`}>
                📞 {attraction.phone}
              </a>
            )}
            {attraction.website && (
              <a
                className="adp__chip adp__chip--link"
                href={attraction.website}
                target="_blank"
                rel="noreferrer"
              >
                🌐 Website
              </a>
            )}
          </div>
        </div>

        {/* ── COORDINATES ── */}
        <div className="adp__section">
          <h2>Location</h2>
          <div className="adp__coords">
            <div className="adp__coord-row">
              <span>🧭 Latitude</span>
              <code>{attraction.latitude?.toFixed(6)}</code>
            </div>
            <div className="adp__coord-row">
              <span>🧭 Longitude</span>
              <code>{attraction.longitude?.toFixed(6)}</code>
            </div>
            {attraction.address && (
              <div className="adp__coord-row">
                <span>📫 Address</span>
                <span>{attraction.address}</span>
              </div>
            )}
          </div>
        </div>

        {/* ── MAP BUTTONS ── */}
        <div className="adp__map-btns">
          <a
            className="adp__map-btn adp__map-btn--osm"
            href={osmMapLink(attraction.latitude, attraction.longitude)}
            target="_blank"
            rel="noreferrer"
          >
            🗺️ View on OpenStreetMap
          </a>
          <a
            className="adp__map-btn adp__map-btn--google"
            href={googleMapsLink(attraction.latitude, attraction.longitude, attraction.name)}
            target="_blank"
            rel="noreferrer"
          >
            📍 Open in Google Maps
          </a>
        </div>
      </div>
    </div>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
function DetailSkeleton() {
  return (
    <div className="adp">
      <div className="adp__skeleton-hero" />
      <div className="adp__body">
        <div className="adp__skeleton-title" />
        <div className="adp__skeleton-text" />
        <div className="adp__skeleton-text adp__skeleton-text--sm" />
      </div>
    </div>
  );
}

// ── Error ─────────────────────────────────────────────────────────────────────
function ErrorState({ error, onBack }) {
  return (
    <div className="adp adp--error">
      <div className="adp__error-box">
        <span>⚠️</span>
        <h3>Oops!</h3>
        <p>{error}</p>
        <button onClick={onBack}>← Go Back</button>
      </div>
    </div>
  );
}