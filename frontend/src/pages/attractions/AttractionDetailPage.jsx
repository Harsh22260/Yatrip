import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAttractionDetail, useAttractionsByCity } from '../../hooks/useAttractions';
import AttractionCard from '../../components/attractions/AttractionCard';
import {
  getCategoryMeta,
  formatEntryFee,
  formatTime,
  isOpenNow,
} from '../../utils/attractionHelpers';
import './AttractionDetailPage.css';

const AttractionDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { attraction, loading, error } = useAttractionDetail(id);

  // Related attractions from same city
  const { attractions: related } = useAttractionsByCity(attraction?.city);
  const relatedFiltered = related.filter((a) => a.id !== parseInt(id)).slice(0, 3);

  if (loading) return <div className="adp-loading">Loading attraction...</div>;
  if (error) return (
    <div className="adp-error">
      ⚠ {error}
      <button onClick={() => navigate('/attractions')}>← Back</button>
    </div>
  );
  if (!attraction) return null;

  const { icon, label, color } = getCategoryMeta(attraction.category);
  const openNow = isOpenNow(attraction.opening_time, attraction.closing_time);

  return (
    <div className="adp-page">
      {/* Hero */}
      <div className="adp-hero" style={{ background: `linear-gradient(135deg, #1e1b4b, ${color})` }}>
        {attraction.image ? (
          <img src={attraction.image} alt={attraction.name} className="adp-hero-img" />
        ) : (
          <div className="adp-hero-placeholder">{icon}</div>
        )}
        <div className="adp-hero-overlay">
          <button className="adp-back-btn" onClick={() => navigate('/attractions')}>
            ← All Attractions
          </button>
          <div className="adp-hero-info">
            <span className="adp-category-badge" style={{ background: color }}>
              {icon} {label}
            </span>
            <h1 className="adp-name">{attraction.name}</h1>
            <p className="adp-city">📍 {attraction.city}</p>
          </div>
        </div>
      </div>

      <div className="adp-body">
        {/* Info Cards Row */}
        <div className="adp-info-row">
          <div className="adp-info-card">
            <span className="adp-info-icon">🎟️</span>
            <span className="adp-info-label">Entry Fee</span>
            <span className="adp-info-value">{formatEntryFee(attraction.entry_fee)}</span>
          </div>

          {attraction.opening_time && (
            <div className="adp-info-card">
              <span className="adp-info-icon">🕐</span>
              <span className="adp-info-label">Timings</span>
              <span className="adp-info-value">
                {formatTime(attraction.opening_time)} – {formatTime(attraction.closing_time)}
              </span>
            </div>
          )}

          {openNow !== null && (
            <div className={`adp-info-card ${openNow ? 'status-open' : 'status-closed'}`}>
              <span className="adp-info-icon">{openNow ? '✅' : '🔴'}</span>
              <span className="adp-info-label">Status</span>
              <span className="adp-info-value">{openNow ? 'Open Now' : 'Closed Now'}</span>
            </div>
          )}

          {attraction.address && (
            <div className="adp-info-card">
              <span className="adp-info-icon">🗺️</span>
              <span className="adp-info-label">Address</span>
              <span className="adp-info-value">{attraction.address}</span>
            </div>
          )}
        </div>

        {/* Description */}
        {attraction.description && (
          <section className="adp-section">
            <h2 className="adp-section-title">About</h2>
            <p className="adp-description">{attraction.description}</p>
          </section>
        )}

        {/* Related */}
        {relatedFiltered.length > 0 && (
          <section className="adp-section">
            <h2 className="adp-section-title">More in {attraction.city}</h2>
            <div className="adp-related-grid">
              {relatedFiltered.map((a) => (
                <AttractionCard
                  key={a.id}
                  attraction={a}
                  onSelect={(attr) => navigate(`/attractions/${attr.id}`)}
                />
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
};

export default AttractionDetailPage;
