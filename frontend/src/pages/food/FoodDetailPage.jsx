import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useVendorDetail } from '../../hooks/useFood';
import MenuItemCard from '../../components/food/MenuItemCard';
import { getVendorTypeMeta, formatPrice, renderStars } from '../../utils/foodHelpers';
import './FoodDetailPage.css';

const StarRating = ({ rating }) => {
  const { full, half, empty } = renderStars(rating);
  return (
    <span className="fdp-stars">
      {'★'.repeat(full)}{half ? '½' : ''}{'☆'.repeat(empty)}
      <span className="fdp-rating-num"> {rating.toFixed(1)}</span>
    </span>
  );
};

const FoodDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { vendor, loading, error } = useVendorDetail(id);
  const [activeTab, setActiveTab] = useState('menu'); // menu | info

  if (loading) return <div className="fdp-loading">Loading vendor...</div>;
  if (error) return (
    <div className="fdp-error">
      ⚠ {error}
      <button onClick={() => navigate('/food')}>← Back</button>
    </div>
  );
  if (!vendor) return null;

  const { icon, label, color } = getVendorTypeMeta(vendor.vendor_type);
  const coverImage = vendor.images?.[0]?.image;
  const availableItems = vendor.menu_items?.filter((i) => i.is_available) || [];
  const unavailableItems = vendor.menu_items?.filter((i) => !i.is_available) || [];

  return (
    <div className="fdp-page">
      {/* Hero */}
      <div className="fdp-hero" style={{ background: `linear-gradient(135deg, #78350f, ${color})` }}>
        {coverImage && <img src={coverImage} alt={vendor.name} className="fdp-hero-img" />}
        <div className="fdp-hero-overlay">
          <button className="fdp-back-btn" onClick={() => navigate('/food')}>← All Vendors</button>
          <div className="fdp-hero-info">
            <div className="fdp-badges">
              <span className="fdp-type-badge" style={{ background: color }}>{icon} {label}</span>
              {vendor.is_verified && <span className="fdp-verified-badge">✓ Verified</span>}
            </div>
            <h1 className="fdp-name">{vendor.name}</h1>
            <div className="fdp-meta">
              <StarRating rating={vendor.rating} />
              <span className="fdp-avg-cost">· Avg {formatPrice(vendor.avg_cost)}</span>
            </div>
            <p className="fdp-address">📍 {vendor.address}</p>
          </div>
        </div>
      </div>

      {/* Image Strip */}
      {vendor.images?.length > 1 && (
        <div className="fdp-image-strip">
          {vendor.images.slice(1, 5).map((img) => (
            <img key={img.id} src={img.image} alt="" className="fdp-strip-img" />
          ))}
        </div>
      )}

      <div className="fdp-body">
        {/* Tabs */}
        <div className="fdp-tabs">
          <button className={`fdp-tab ${activeTab === 'menu' ? 'active' : ''}`} onClick={() => setActiveTab('menu')}>
            🍽️ Menu ({vendor.menu_items?.length || 0})
          </button>
          <button className={`fdp-tab ${activeTab === 'info' ? 'active' : ''}`} onClick={() => setActiveTab('info')}>
            ℹ️ Info
          </button>
        </div>

        {/* Menu Tab */}
        {activeTab === 'menu' && (
          <div className="fdp-menu">
            {vendor.menu_items?.length === 0 && (
              <p className="fdp-no-menu">No menu items added yet.</p>
            )}

            {availableItems.length > 0 && (
              <section>
                <h3 className="fdp-menu-section-title">Available Items</h3>
                <div className="fdp-menu-grid">
                  {availableItems.map((item) => (
                    <MenuItemCard key={item.id} item={item} />
                  ))}
                </div>
              </section>
            )}

            {unavailableItems.length > 0 && (
              <section style={{ marginTop: '24px' }}>
                <h3 className="fdp-menu-section-title">Currently Unavailable</h3>
                <div className="fdp-menu-grid">
                  {unavailableItems.map((item) => (
                    <MenuItemCard key={item.id} item={item} />
                  ))}
                </div>
              </section>
            )}
          </div>
        )}

        {/* Info Tab */}
        {activeTab === 'info' && (
          <div className="fdp-info">
            {vendor.description && (
              <div className="fdp-info-card">
                <h3>About</h3>
                <p>{vendor.description}</p>
              </div>
            )}
            <div className="fdp-info-row">
              <div className="fdp-info-item">
                <span className="fdp-info-icon">📍</span>
                <div>
                  <span className="fdp-info-label">Address</span>
                  <span className="fdp-info-val">{vendor.address}</span>
                </div>
              </div>
              <div className="fdp-info-item">
                <span className="fdp-info-icon">💰</span>
                <div>
                  <span className="fdp-info-label">Avg Cost</span>
                  <span className="fdp-info-val">{formatPrice(vendor.avg_cost)}</span>
                </div>
              </div>
              {vendor.category_name && (
                <div className="fdp-info-item">
                  <span className="fdp-info-icon">🍴</span>
                  <div>
                    <span className="fdp-info-label">Category</span>
                    <span className="fdp-info-val">{vendor.category_name}</span>
                  </div>
                </div>
              )}
              <div className="fdp-info-item">
                <span className="fdp-info-icon">⭐</span>
                <div>
                  <span className="fdp-info-label">Rating</span>
                  <span className="fdp-info-val">{vendor.rating.toFixed(1)} / 5</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default FoodDetailPage;
