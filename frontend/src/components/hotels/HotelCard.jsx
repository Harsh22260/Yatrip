import React from 'react';
import { formatPrice, renderStars } from '../../utils/hotelHelpers';
import './HotelCard.css';

const StarRating = ({ rating }) => {
  const { full, half, empty } = renderStars(rating);
  return (
    <span className="hc-stars" aria-label={`${rating} out of 5`}>
      {'★'.repeat(full)}
      {half ? '½' : ''}
      {'☆'.repeat(empty)}
    </span>
  );
};

const HotelCard = ({ hotel, onSelect }) => {
  const lowestPrice = hotel.room_types?.reduce((min, rt) =>
    parseFloat(rt.base_price) < min ? parseFloat(rt.base_price) : min,
    Infinity
  );

  return (
    <article className="hc-card" onClick={() => onSelect?.(hotel)} role="button" tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onSelect?.(hotel)}>
      <div className="hc-image-wrap">
        <div className="hc-image-placeholder">
          <span>🏨</span>
        </div>
        {hotel.is_verified && (
          <span className="hc-verified-badge">✓ Verified</span>
        )}
      </div>

      <div className="hc-body">
        <div className="hc-header">
          <h3 className="hc-name">{hotel.name}</h3>
          <StarRating rating={hotel.rating} />
        </div>

        <p className="hc-address">📍 {hotel.address}</p>

        {hotel.description && (
          <p className="hc-desc">{hotel.description.slice(0, 100)}...</p>
        )}

        <div className="hc-footer">
          <div className="hc-price">
            {lowestPrice !== Infinity ? (
              <>
                <span className="hc-from">from</span>
                <span className="hc-amount">{formatPrice(lowestPrice)}</span>
                <span className="hc-per">/ night</span>
              </>
            ) : (
              <span className="hc-no-price">Check availability</span>
            )}
          </div>
          <button className="hc-btn" onClick={(e) => { e.stopPropagation(); onSelect?.(hotel); }}>
            View Rooms →
          </button>
        </div>
      </div>
    </article>
  );
};

export default HotelCard;
