import { useNavigate } from "react-router-dom";
import "./AttractionCard.css";
import {
  getCategoryInfo,
  formatDistance,
  buildStars,
  formatFee,
  formatLocation,
} from "../../utils/attractionHelpers";

// Placeholder gradient backgrounds per category
const PLACEHOLDERS = {
  monument: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
  temple:   "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
  park:     "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)",
  museum:   "linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)",
  nature:   "linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)",
  other:    "linear-gradient(135deg, #fccb90 0%, #d57eeb 100%)",
  all:      "linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%)",
};

export default function AttractionCard({ attraction, variant = "grid" }) {
  const navigate = useNavigate();
  const cat  = getCategoryInfo(attraction.category);
  const dist = formatDistance(attraction.distance_km);
  const fee  = formatFee(attraction);
  const loc  = formatLocation(attraction, true);

  const handleClick = () => navigate(`/attractions/${attraction.id}`);

  if (variant === "list") {
    return (
      <div className="attraction-card attraction-card--list" onClick={handleClick}>
        <div className="ac-image ac-image--sm">
          {attraction.image_url ? (
            <img src={attraction.image_url} alt={attraction.name} loading="lazy" />
          ) : (
            <div
              className="ac-image__placeholder"
              style={{ background: PLACEHOLDERS[attraction.category] || PLACEHOLDERS.other }}
            >
              <span>{cat.icon}</span>
            </div>
          )}
        </div>
        <div className="ac-body">
          <div className="ac-body__top">
            <span className="ac-badge ac-badge--cat">{cat.icon} {cat.label}</span>
            {dist && <span className="ac-badge ac-badge--dist">📍 {dist}</span>}
          </div>
          <h3 className="ac-title">{attraction.name}</h3>
          {loc && <p className="ac-loc">📌 {loc}</p>}
          <div className="ac-footer">
            <span className="ac-stars" title={`${attraction.rating} / 5`}>
              {buildStars(attraction.rating)}
              <em>{attraction.rating ? ` ${parseFloat(attraction.rating).toFixed(1)}` : " —"}</em>
            </span>
            <span className={`ac-fee ac-fee--${fee.type}`}>{fee.label}</span>
          </div>
        </div>
      </div>
    );
  }

  // Grid variant (default)
  return (
    <div className="attraction-card attraction-card--grid" onClick={handleClick}>
      <div className="ac-image">
        {attraction.image_url ? (
          <img src={attraction.image_url} alt={attraction.name} loading="lazy" />
        ) : (
          <div
            className="ac-image__placeholder"
            style={{ background: PLACEHOLDERS[attraction.category] || PLACEHOLDERS.other }}
          >
            <span>{cat.icon}</span>
          </div>
        )}
        <div className="ac-image__badges">
          <span className="ac-badge ac-badge--cat">{cat.icon} {cat.label}</span>
          {dist && <span className="ac-badge ac-badge--dist">📍 {dist}</span>}
        </div>
      </div>

      <div className="ac-body">
        <h3 className="ac-title">{attraction.name}</h3>
        {loc && <p className="ac-loc">📌 {loc}</p>}
        <div className="ac-footer">
          <span className="ac-stars" title={`${attraction.rating} / 5`}>
            {buildStars(attraction.rating)}
            <em>{attraction.rating ? ` ${parseFloat(attraction.rating).toFixed(1)}` : " —"}</em>
          </span>
          <span className={`ac-fee ac-fee--${fee.type}`}>{fee.label}</span>
        </div>
      </div>
    </div>
  );
}