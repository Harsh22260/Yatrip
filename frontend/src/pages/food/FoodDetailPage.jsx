import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useVendorDetail } from '../../hooks/useFood';
import MenuItemCard from '../../components/food/MenuItemCard';
import { getVendorTypeMeta, formatPrice, renderStars } from '../../utils/foodHelpers';
import { artFor, artworkDataUri } from '../../utils/placeArt';
import { categoryFallback, fallbackCredit } from '../../utils/foodFallbackImages';
import './FoodDetailPage.css';

const StarRating = ({ rating }) => {
  // OSM rows carry rating 0 and a manually registered outlet can carry null, so
  // this cannot assume a number. `.toFixed` on null threw and blanked the page.
  const value = Number.isFinite(Number(rating)) ? Number(rating) : 0;
  const { full, half, empty } = renderStars(value);
  return (
    <span className="fdp-stars">
      {'★'.repeat(full)}{half ? '½' : ''}{'☆'.repeat(empty)}
      <span className="fdp-rating-num"> {value.toFixed(1)}</span>
    </span>
  );
};

const FoodDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { vendor, loading, error } = useVendorDetail(id);
  const [activeTab, setActiveTab] = useState('menu'); // menu | info
  // The URL that failed to load, rather than a boolean, so moving from one place
  // to the next does not inherit the previous page's broken image.
  const [failedSrc, setFailedSrc] = useState(null);

  if (loading) return <div className="fdp-loading">Loading vendor...</div>;
  if (error) return (
    <div className="fdp-error">
      ⚠ {error}
      <button onClick={() => navigate('/food')}>← Back</button>
    </div>
  );
  if (!vendor) return null;

  const { icon, label, color } = getVendorTypeMeta(vendor.category);
  const coverImage = vendor.image_url;
  // Almost every row imported from OpenStreetMap has no photograph of its own, so
  // the hero uses the bundled real photograph for the category rather than a flat
  // gradient or generated artwork. Artwork stays as the last resort if the
  // photograph itself cannot be loaded.
  const heroPhoto = coverImage || categoryFallback(vendor.category).src;
  const heroBroken = Boolean(heroPhoto) && heroPhoto === failedSrc;
  // CC BY and CC BY-SA require attribution, so whichever photograph is shown has
  // to carry its credit: the stored one for the place's own photo, the bundled
  // one for the category photo.
  const heroCredit = coverImage ? vendor.image_credit : fallbackCredit(vendor.category);
  const art = artFor(vendor.category, vendor.name);
  // The backend did not return menu_items at all, so `menu_items?.length === 0`
  // was `undefined === 0` -> false: the "no menu" message never rendered and the
  // tab just looked broken. Default to an empty list first.
  const menuItems = vendor.menu_items ?? [];
  const availableItems = menuItems.filter((i) => i.is_available !== false);
  const unavailableItems = menuItems.filter((i) => i.is_available === false);

  return (
    <div className="fdp-page">
      {/* Hero */}
      <div
        className="fdp-hero"
        style={
          heroBroken
            ? { backgroundImage: `url("${artworkDataUri(art, vendor.name)}")`, backgroundSize: 'cover', backgroundPosition: 'center' }
            : { background: `linear-gradient(135deg, #78350f, ${color})` }
        }
      >
        {heroPhoto && !heroBroken && (
          <img
            src={heroPhoto}
            alt={vendor.name}
            className="fdp-hero-img"
            onError={() => setFailedSrc(heroPhoto)}
          />
        )}
        {/* Wikimedia photography has attribution requirements, so the credit has
            to sit next to the photograph it belongs to. */}
        {heroCredit && !heroBroken && (
          <span className="fdp-hero-credit">{heroCredit}</span>
        )}
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
              <span className="fdp-avg-cost">· Price {formatPrice(vendor.price_level)}</span>
            </div>
            <p className="fdp-address">📍 {vendor.address}</p>
          </div>
        </div>
      </div>

      {/* Image Strip (Backend currently only provides one image) */}
      {/* {vendor.images?.length > 1 && (
        <div className="fdp-image-strip">
          {vendor.images.slice(1, 5).map((img) => (
            <img key={img.id} src={img.image} alt="" className="fdp-strip-img" />
          ))}
        </div>
      )} */}

      <div className="fdp-body">
        {/* Tabs */}
        <div className="fdp-tabs">
          <button className={`fdp-tab ${activeTab === 'menu' ? 'active' : ''}`} onClick={() => setActiveTab('menu')}>
            🍽️ Menu ({menuItems.length})
          </button>
          <button className={`fdp-tab ${activeTab === 'info' ? 'active' : ''}`} onClick={() => setActiveTab('info')}>
            ℹ️ Info
          </button>
        </div>

        {/* Menu Tab */}
        {activeTab === 'menu' && (
          <div className="fdp-menu">
            {menuItems.length === 0 && (
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
                  <span className="fdp-info-label">Price Level</span>
                  <span className="fdp-info-val">{formatPrice(vendor.price_level)}</span>
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
                <span className="fdp-info-val">
                  {(Number.isFinite(Number(vendor.rating)) ? Number(vendor.rating) : 0).toFixed(1)} / 5
                </span>
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
