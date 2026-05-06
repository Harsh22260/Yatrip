import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMyHotels } from '../../hooks/useHotels';
import { formatPrice } from '../../utils/hotelHelpers';
import './MyHotelsPage.css';

const MyHotelsPage = () => {
  const { hotels, loading, error, refetch } = useMyHotels();
  const navigate = useNavigate();

  return (
    <div className="mhp-page">
      <div className="mhp-header">
        <div className="mhp-header-inner">
          <div>
            <h1 className="mhp-title">My Hotels</h1>
            <p className="mhp-sub">{hotels.length} propert{hotels.length !== 1 ? 'ies' : 'y'} listed</p>
          </div>
          <button className="mhp-add-btn" onClick={() => navigate('/register-hotel')}>
            + Register New Hotel
          </button>
        </div>
      </div>

      <div className="mhp-body">
        {loading && (
          <div className="mhp-loading">
            {[1,2,3].map(i => <div key={i} className="mhp-skeleton" />)}
          </div>
        )}

        {error && (
          <div className="mhp-error">
            <p>⚠ {error}</p>
            <button onClick={refetch}>Retry</button>
          </div>
        )}

        {!loading && hotels.length === 0 && (
          <div className="mhp-empty">
            <div className="mhp-empty-icon">🏨</div>
            <h2>No hotels yet</h2>
            <p>Register your first property on Yatrip and reach thousands of travelers.</p>
            <button className="mhp-add-btn" onClick={() => navigate('/register-hotel')}>
              + Register Hotel
            </button>
          </div>
        )}

        <div className="mhp-grid">
          {hotels.map((hotel) => {
            const lowestPrice = hotel.room_types?.reduce(
              (min, rt) => parseFloat(rt.base_price) < min ? parseFloat(rt.base_price) : min,
              Infinity
            );

            return (
              <div key={hotel.id} className="mhp-card">
                <div className="mhp-card-img">
                  <span>🏨</span>
                  {hotel.is_verified
                    ? <span className="mhp-badge verified">✓ Verified</span>
                    : <span className="mhp-badge pending">⏳ Pending</span>
                  }
                </div>

                <div className="mhp-card-body">
                  <div className="mhp-card-top">
                    <h3 className="mhp-hotel-name">{hotel.name}</h3>
                    <span className="mhp-rating">★ {hotel.rating}</span>
                  </div>

                  <p className="mhp-address">📍 {hotel.address}</p>

                  <div className="mhp-stats">
                    <div className="mhp-stat">
                      <span className="mhp-stat-val">{hotel.room_types?.length || 0}</span>
                      <span className="mhp-stat-label">Room Types</span>
                    </div>
                    <div className="mhp-stat">
                      <span className="mhp-stat-val">
                        {lowestPrice !== Infinity ? formatPrice(lowestPrice) : '—'}
                      </span>
                      <span className="mhp-stat-label">From / night</span>
                    </div>
                    <div className="mhp-stat">
                      <span className="mhp-stat-val">
                        {hotel.is_verified ? '✓' : '⏳'}
                      </span>
                      <span className="mhp-stat-label">Status</span>
                    </div>
                  </div>

                  <div className="mhp-card-actions">
                    <button
                      className="mhp-btn secondary"
                      onClick={() => navigate(`/hotels/${hotel.id}`)}
                    >
                      View Listing
                    </button>
                    <button
                      className="mhp-btn primary"
                      onClick={() => navigate(`/my-hotels/${hotel.id}/edit`)}
                    >
                      Edit Hotel
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default MyHotelsPage;