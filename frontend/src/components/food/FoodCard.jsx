import { useNavigate } from "react-router-dom";
import { getCategoryInfo, formatDistance, buildStars, vegLabel } from "../../utils/foodHelpers";
import "./FoodCard.css";

const BG = {
  street_food: "linear-gradient(135deg,#f7971e,#ffd200)",
  restaurant:  "linear-gradient(135deg,#ee0979,#ff6a00)",
  cafe:        "linear-gradient(135deg,#6a3093,#a044ff)",
  dhaba:       "linear-gradient(135deg,#11998e,#38ef7d)",
  bakery:      "linear-gradient(135deg,#f953c6,#b91d73)",
  sweet_shop:  "linear-gradient(135deg,#fc5c7d,#6a82fb)",
  juice_bar:   "linear-gradient(135deg,#43e97b,#38f9d7)",
  fast_food:   "linear-gradient(135deg,#f7797d,#FBD786)",
  other:       "linear-gradient(135deg,#bdc3c7,#2c3e50)",
};

export default function FoodCard({ place, variant = "grid" }) {
  const navigate = useNavigate();
  const cat  = getCategoryInfo(place.category);
  const dist = formatDistance(place.distance_km);
  const veg  = vegLabel(place.is_veg);

  const go = () => navigate(`/food/${place.id}`);

  if (variant === "list") {
    return (
      <div className="fc fc--list" onClick={go}>
        <div className="fc__img fc__img--sm" style={{ background: BG[place.category] || BG.other }}>
          {place.image_url
            ? <img src={place.image_url} alt={place.name} loading="lazy" />
            : <span>{cat.icon}</span>}
        </div>
        <div className="fc__body">
          <div className="fc__top-badges">
            <span className="fc__badge fc__badge--cat">{cat.icon} {cat.label}</span>
            {dist && <span className="fc__badge fc__badge--dist">📍 {dist}</span>}
          </div>
          <h3 className="fc__name">{place.name}</h3>
          <p className="fc__city">📌 {[place.city, place.state].filter(Boolean).join(", ")}</p>
          <div className="fc__footer">
            <span className="fc__stars">{buildStars(place.rating)}<em> {place.rating ? parseFloat(place.rating).toFixed(1) : "—"}</em></span>
            <span className={`fc__veg fc__veg--${veg.cls}`}>{veg.label}</span>
            <span className="fc__price">{place.price_display || "₹"}</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fc fc--grid" onClick={go}>
      <div className="fc__img" style={{ background: BG[place.category] || BG.other }}>
        {place.image_url
          ? <img src={place.image_url} alt={place.name} loading="lazy" />
          : <span className="fc__placeholder">{cat.icon}</span>}
        <div className="fc__img-badges">
          <span className="fc__badge fc__badge--cat">{cat.icon} {cat.label}</span>
          {dist && <span className="fc__badge fc__badge--dist">📍 {dist}</span>}
        </div>
        {place.home_delivery && <span className="fc__delivery-tag">🛵 Delivery</span>}
      </div>
      <div className="fc__body">
        <h3 className="fc__name">{place.name}</h3>
        <p className="fc__city">📌 {[place.city, place.state].filter(Boolean).join(", ")}</p>
        <div className="fc__footer">
          <span className="fc__stars">{buildStars(place.rating)}<em> {place.rating ? parseFloat(place.rating).toFixed(1) : "—"}</em></span>
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