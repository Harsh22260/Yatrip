import React from 'react';
import { getCategoryMeta, formatEntryFee, isOpenNow, formatTime } from '../../utils/attractionHelpers';
import './AttractionCard.css';

const AttractionCard = ({ attraction, onSelect }) => {
  const { icon, label, color } = getCategoryMeta(attraction.category);
  const openNow = isOpenNow(attraction.opening_time, attraction.closing_time);

  return (
    <article
      className="ac-card"
      onClick={() => onSelect?.(attraction)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onSelect?.(attraction)}
    >
      <div className="ac-image-wrap" style={{ background: `linear-gradient(135deg, ${color}22, ${color}44)` }}>
        {attraction.image ? (
          <img src={attraction.image} alt={attraction.name} className="ac-image" />
        ) : (
          <div className="ac-icon-placeholder" style={{ color }}>
            <span>{icon}</span>
          </div>
        )}
        <span className="ac-category-badge" style={{ background: color }}>
          {icon} {label}
        </span>
        {openNow !== null && (
          <span className={`ac-open-badge ${openNow ? 'open' : 'closed'}`}>
            {openNow ? '● Open' : '● Closed'}
          </span>
        )}
      </div>

      <div className="ac-body">
        <h3 className="ac-name">{attraction.name}</h3>
        <p className="ac-city">📍 {attraction.city}</p>

        {attraction.description && (
          <p className="ac-desc">{attraction.description.slice(0, 90)}...</p>
        )}

        <div className="ac-footer">
          <div className="ac-info">
            <span className="ac-fee">{formatEntryFee(attraction.entry_fee)}</span>
            {attraction.opening_time && (
              <span className="ac-time">
                🕐 {formatTime(attraction.opening_time)} – {formatTime(attraction.closing_time)}
              </span>
            )}
          </div>
          <button className="ac-btn" onClick={(e) => { e.stopPropagation(); onSelect?.(attraction); }}>
            Details →
          </button>
        </div>
      </div>
    </article>
  );
};

export default AttractionCard;
