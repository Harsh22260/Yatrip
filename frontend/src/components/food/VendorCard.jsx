import React from 'react';
import { getVendorTypeMeta, formatPrice, getPriceBucket, renderStars } from '../../utils/foodHelpers';
import './VendorCard.css';

const StarRating = ({ rating }) => {
  const { full, half, empty } = renderStars(rating);
  return (
    <span className="vc-stars">
      {'★'.repeat(full)}{half ? '½' : ''}{'☆'.repeat(empty)}
      <span className="vc-rating-num"> {rating.toFixed(1)}</span>
    </span>
  );
};

const VendorCard = ({ vendor, onSelect }) => {
  const { icon, label, color } = getVendorTypeMeta(vendor.vendor_type);
  const priceBucket = getPriceBucket(vendor.avg_cost);
  const coverImage = vendor.images?.[0]?.image;

  return (
    <article
      className="vc-card"
      onClick={() => onSelect?.(vendor)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onSelect?.(vendor)}
    >
      <div className="vc-image-wrap">
        {coverImage ? (
          <img src={coverImage} alt={vendor.name} className="vc-image" />
        ) : (
          <div className="vc-placeholder" style={{ background: `linear-gradient(135deg, ${color}22, ${color}55)` }}>
            <span>{icon}</span>
          </div>
        )}
        <span className="vc-type-badge" style={{ background: color }}>
          {icon} {label}
        </span>
        {vendor.is_verified && (
          <span className="vc-verified">✓ Verified</span>
        )}
      </div>

      <div className="vc-body">
        <div className="vc-header">
          <h3 className="vc-name">{vendor.name}</h3>
          <StarRating rating={vendor.rating} />
        </div>

        {vendor.category_name && (
          <span className="vc-category">🍽️ {vendor.category_name}</span>
        )}

        <p className="vc-address">📍 {vendor.address}</p>

        {vendor.description && (
          <p className="vc-desc">{vendor.description.slice(0, 85)}...</p>
        )}

        <div className="vc-footer">
          <div className="vc-price-info">
            <span className="vc-avg">Avg: {formatPrice(vendor.avg_cost)}</span>
            <span className="vc-bucket" style={{ color: priceBucket.color }}>
              {priceBucket.label}
            </span>
          </div>
          <button className="vc-btn" onClick={(e) => { e.stopPropagation(); onSelect?.(vendor); }}>
            View Menu →
          </button>
        </div>
      </div>
    </article>
  );
};

export default VendorCard;
