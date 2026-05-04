import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useRentalDetail } from '../../hooks/useRentals';
import { getRentalTypeMeta, formatMonthlyRent, getAmenityIcon } from '../../utils/rentalHelpers';
import './RentalDetailPage.css';

const RentalDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { rental, loading, error } = useRentalDetail(id);
  const [activeImg, setActiveImg] = useState(0);
  const [showContactForm, setShowContactForm] = useState(false);

  if (loading) return <div className="rdp-loading">Loading rental...</div>;
  if (error) return <div className="rdp-error">⚠ {error} <button onClick={() => navigate('/rentals')}>← Back</button></div>;
  if (!rental) return null;

  const { icon, label, color, bg } = getRentalTypeMeta(rental.rental_type);
  const images = rental.images || [];

  return (
    <div className="rdp-page">
      {/* Back */}
      <div className="rdp-topbar">
        <button className="rdp-back" onClick={() => navigate('/rentals')}>← All Rentals</button>
        <div className="rdp-badges">
          <span className="rdp-type-badge" style={{ background: color }}>{icon} {label}</span>
          {rental.is_verified && <span className="rdp-verified">✓ Verified</span>}
        </div>
      </div>

      <div className="rdp-body">
        {/* Left Column */}
        <div className="rdp-left">
          {/* Image Gallery */}
          <div className="rdp-gallery">
            <div className="rdp-main-img-wrap">
              {images.length > 0 ? (
                <img src={images[activeImg]?.image} alt={rental.name} className="rdp-main-img" />
              ) : (
                <div className="rdp-img-placeholder" style={{ background: bg }}>
                  <span style={{ color, fontSize: '6rem' }}>{icon}</span>
                </div>
              )}
            </div>
            {images.length > 1 && (
              <div className="rdp-thumbs">
                {images.map((img, i) => (
                  <button
                    key={img.id}
                    className={`rdp-thumb ${i === activeImg ? 'active' : ''}`}
                    onClick={() => setActiveImg(i)}
                  >
                    <img src={img.image} alt="" />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Description */}
          {rental.description && (
            <div className="rdp-section">
              <h2 className="rdp-section-title">About this place</h2>
              <p className="rdp-description">{rental.description}</p>
            </div>
          )}

          {/* Amenities */}
          {rental.amenities?.length > 0 && (
            <div className="rdp-section">
              <h2 className="rdp-section-title">Amenities</h2>
              <div className="rdp-amenities-grid">
                {rental.amenities.map((a) => (
                  <div key={a.id} className="rdp-amenity">
                    <span className="rdp-amenity-icon">{getAmenityIcon(a.name)}</span>
                    <span>{a.name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column - Sticky Info */}
        <div className="rdp-right">
          <div className="rdp-info-card">
            <h1 className="rdp-name">{rental.name}</h1>
            <p className="rdp-address">📍 {rental.address}</p>

            <div className="rdp-price-row">
              <span className="rdp-price">{formatMonthlyRent(rental.price_per_month)}</span>
              <span className="rdp-per">/ month</span>
            </div>

            <div className="rdp-meta-grid">
              <div className="rdp-meta-item">
                <span className="rdp-meta-icon">🛏</span>
                <div>
                  <span className="rdp-meta-label">Available Rooms</span>
                  <span className={`rdp-meta-val ${rental.available_rooms === 0 ? 'red' : 'green'}`}>
                    {rental.available_rooms === 0 ? 'Fully Occupied' : `${rental.available_rooms} rooms`}
                  </span>
                </div>
              </div>
              <div className="rdp-meta-item">
                <span className="rdp-meta-icon">🏠</span>
                <div>
                  <span className="rdp-meta-label">Type</span>
                  <span className="rdp-meta-val">{label}</span>
                </div>
              </div>
              {rental.owner_email && (
                <div className="rdp-meta-item">
                  <span className="rdp-meta-icon">👤</span>
                  <div>
                    <span className="rdp-meta-label">Owner</span>
                    <span className="rdp-meta-val">{rental.owner_email}</span>
                  </div>
                </div>
              )}
            </div>

            <button
              className="rdp-contact-btn"
              onClick={() => setShowContactForm(!showContactForm)}
              disabled={rental.available_rooms === 0}
            >
              {rental.available_rooms === 0 ? '❌ No Rooms Available' : '📩 Contact Owner'}
            </button>

            {showContactForm && (
              <div className="rdp-contact-form">
                <p className="rdp-contact-info">
                  📧 Contact: <strong>{rental.owner_email}</strong>
                </p>
                <textarea
                  className="rdp-message"
                  placeholder="Hi, I'm interested in this rental..."
                  rows={3}
                />
                <button className="rdp-send-btn">Send Inquiry</button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RentalDetailPage;
