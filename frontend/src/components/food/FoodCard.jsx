import { useNavigate } from "react-router-dom";
import PlaceImage from "../PlaceImage";
import { getCategoryInfo, formatDistance, buildStars, vegLabel } from "../../utils/foodHelpers";
import { categoryFallback, fallbackCredit } from "../../utils/foodFallbackImages";
import "./FoodCard.css";

export default function FoodCard({ place, variant = "grid" }) {
  const navigate = useNavigate();
  const cat  = getCategoryInfo(place.category);
  const dist = formatDistance(place.distance_km);
  const veg  = vegLabel(place.is_veg);

  // Most food rows have no photograph of their own, so the card falls back to a
  // bundled real photograph of that category rather than generated artwork.
  const categoryPhoto = categoryFallback(place.category);

  const go = () => navigate(`/food/${place.id}`);

  const stars = (
    <span className="fc__stars">
      {buildStars(place.rating)}
      <em> {place.rating ? parseFloat(place.rating).toFixed(1) : "—"}</em>
    </span>
  );

  if (variant === "list") {
    return (
      <div className="fc fc--list" onClick={go}>
        <PlaceImage
          src={place.image_url}
          fallbackSrc={categoryPhoto.src}
          fallbackCredit={fallbackCredit(place.category)}
          alt={place.name}
          category={place.category}
          name={place.name}
          className="fc__img fc__img--sm"
          badge={<span className="fc__badge fc__badge--cat">{cat.icon} {cat.label}</span>}
        />
        <div className="fc__body">
          <div className="fc__top-badges">
            {dist && <span className="fc__badge fc__badge--dist">📍 {dist}</span>}
          </div>
          <h3 className="fc__name">{place.name}</h3>
          <p className="fc__city">📌 {[place.city, place.state].filter(Boolean).join(", ") || "—"}</p>
          <div className="fc__footer">
            {stars}
            <span className={`fc__veg fc__veg--${veg.cls}`}>{veg.label}</span>
            <span className="fc__price">{place.price_display || "₹"}</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fc fc--grid" onClick={go}>
      <PlaceImage
        src={place.image_url}
        fallbackSrc={categoryPhoto.src}
        fallbackCredit={fallbackCredit(place.category)}
        alt={place.name}
        category={place.category}
        name={place.name}
        className="fc__img"
        badge={<span className="fc__badge fc__badge--cat">{cat.icon} {cat.label}</span>}
      />
      <div className="fc__body">
        <h3 className="fc__name">{place.name}</h3>
        <p className="fc__city">📌 {[place.city, place.state].filter(Boolean).join(", ") || "—"}</p>
        <div className="fc__footer">
          {stars}
          <span className={`fc__veg fc__veg--${veg.cls}`}>{veg.label}</span>
        </div>
        <div className="fc__meta">
          <span className="fc__price">{place.price_display || "₹"}</span>
          {place.takeaway && <span className="fc__chip">📦 Takeaway</span>}
        </div>
      </div>
    </div>
  );
}