import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useVendors, useFoodCategories } from '../../hooks/useFood';
import VendorCard from '../../components/food/VendorCard';
import { filterVendors } from '../../utils/foodHelpers';
import './FoodListPage.css';

const FoodListPage = () => {
  const { vendors, loading, error, refetch } = useVendors();
  const { categories } = useFoodCategories();
  const navigate = useNavigate();

  const [search, setSearch] = useState('');
  const [type, setType] = useState('all');
  const [category, setCategory] = useState('all');
  const [maxCost, setMaxCost] = useState('');

  const filtered = filterVendors(vendors, { search, type, category, maxCost });

  return (
    <div className="flp-page">
      <header className="flp-header">
        <h1 className="flp-title">Food & Vendors</h1>
        <p className="flp-sub">Local eats, street food & restaurants</p>
        <div className="flp-search-wrap">
          <input
            className="flp-search"
            type="text"
            placeholder="Search vendors or areas..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <span className="flp-search-icon">🔍</span>
        </div>
      </header>

      <div className="flp-body">
        {/* Filters */}
        <div className="flp-filters">
          {/* Vendor Type */}
          <div className="flp-filter-group">
            {['all', 'registered', 'street'].map((t) => (
              <button
                key={t}
                className={`flp-filter-btn ${type === t ? 'active' : ''}`}
                onClick={() => setType(t)}
              >
                {t === 'all' ? '🍴 All' : t === 'registered' ? '🏪 Registered' : '🛺 Street'}
              </button>
            ))}
          </div>

          {/* Category */}
          {categories.length > 0 && (
            <div className="flp-filter-group">
              <button
                className={`flp-filter-btn ${category === 'all' ? 'active' : ''}`}
                onClick={() => setCategory('all')}
              >All Categories</button>
              {categories.map((c) => (
                <button
                  key={c.id}
                  className={`flp-filter-btn ${category === c.name ? 'active' : ''}`}
                  onClick={() => setCategory(category === c.name ? 'all' : c.name)}
                >
                  {c.name}
                </button>
              ))}
            </div>
          )}

          {/* Max Cost */}
          <div className="flp-cost-filter">
            <label>Max Avg Cost: {maxCost ? `₹${maxCost}` : 'Any'}</label>
            <input
              type="range"
              min="50"
              max="1000"
              step="50"
              value={maxCost || 1000}
              onChange={(e) => setMaxCost(e.target.value === '1000' ? '' : e.target.value)}
            />
          </div>
        </div>

        {/* Count */}
        {!loading && (
          <p className="flp-count">{filtered.length} vendor{filtered.length !== 1 ? 's' : ''} found</p>
        )}

        {/* Loading */}
        {loading && (
          <div className="flp-grid">
            {[1,2,3,4,5,6].map((i) => <div key={i} className="flp-skeleton" />)}
          </div>
        )}

        {error && (
          <div className="flp-error">
            <p>⚠ {error}</p>
            <button onClick={refetch}>Retry</button>
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div className="flp-empty">
            <p>🍽️ No vendors found.</p>
            <p>Try different filters.</p>
          </div>
        )}

        {!loading && !error && filtered.length > 0 && (
          <div className="flp-grid">
            {filtered.map((v) => (
              <VendorCard
                key={v.id}
                vendor={v}
                onSelect={(vendor) => navigate(`/food/${vendor.id}`)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default FoodListPage;
