import React, { useState } from 'react';
import { getRentalTypeMeta, formatMonthlyRent, getPriceTier, getAmenityIcon } from '../../utils/rentalHelpers';
import './RentalCard.css';

const RentalCard = ({ rental, onSelect }) => {
  const [imgIdx, setImgIdx] = useState(0);
  const { icon, label, color, bg } = getRentalTypeMeta(rental.rental_type);
  const priceTier = getPriceTier(rental.price_per_month);
  const images = rental.images || [];

  return (
    <article className="rc-card" onClick={() => onSelect?.(rental)} role="button" tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onSelect?.(rental)}>

      {/* Image Carousel */}
      <div className="rc-image-wrap">
        {images.length > 0 ? (
          <>
            <img src={images[imgIdx]?.image} alt={rental.name} className="rc-image" />
            {images.length > 1 && (
              <div className="rc-img-dots">
                {images.slice(0, 5).map((_, i) => (
                  <button
                    key={i}
                    className={`rc-dot ${i === imgIdx ? 'active' : ''}`}
                    onClick={(e) => { e.stopPropagation(); setImgIdx(i); }}
                  />
                ))}
              </div>
            )}
            {images.length > 1 && (
              <>
                <button className="rc-img-arrow left" onClick={(e) => { e.stopPropagation(); setImgIdx((imgIdx - 1 + images.length) % images.length); }}>‹</button>
                <button className="rc-img-arrow right" onClick={(e) => { e.stopPropagation(); setImgIdx((imgIdx + 1) % images.length); }}>›</button>
              </>
            )}
          </>
        ) : (
          <div className="rc-placeholder" style={{ background: bg }}>
            <span style={{ color }}>{icon}</span>
          </div>
        )}

        <span className="rc-type-badge" style={{ background: color }}>{icon} {label}</span>
        {rental.is_verified && <span className="rc-verified">✓ Verified</span>}

        {/* Price overlay */}
        <div className="rc-price-overlay">
          <span className="rc-price">{formatMonthlyRent(rental.price_per_month)}</span>
          <span className="rc-per">/mo</span>
        </div>
      </div>

      <div className="rc-body">
        <div className="rc-header">
          <h3 className="rc-name">{rental.name}</h3>
          <span className="rc-tier" style={{ color: priceTier.color }}>
            {'₹'.repeat(priceTier.dots)}
          </span>
        </div>

        <p className="rc-address">📍 {rental.address}</p>

        {/* Rooms available */}
        <div className="rc-rooms">
          <span className={`rc-rooms-badge ${rental.available_rooms === 0 ? 'full' : ''}`}>
            {rental.available_rooms === 0 ? '❌ Full' : `🛏 ${rental.available_rooms} room${rental.available_rooms > 1 ? 's' : ''} available`}
          </span>
        </div>

        {/* Amenities preview */}
        {rental.amenities?.length > 0 && (
          <div className="rc-amenities">
            {rental.amenities.slice(0, 5).map((a) => (
              <span key={a.id} className="rc-amenity-chip">
                {getAmenityIcon(a.name)} {a.name}
              </span>
            ))}
            {rental.amenities.length > 5 && (
              <span className="rc-amenity-more">+{rental.amenities.length - 5}</span>
            )}
          </div>
        )}

        <button className="rc-btn" onClick={(e) => { e.stopPropagation(); onSelect?.(rental); }}>
          View Details →
        </button>
      </div>
    </article>
  );
};

export default RentalCard;
