import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAttractions } from '../../hooks/useAttractions';
import AttractionCard from '../../components/attractions/AttractionCard';
import CategoryFilter from '../../components/attractions/CategoryFilter';
import { filterAttractions } from '../../utils/attractionHelpers';
import './AttractionsListPage.css';

const AttractionsListPage = () => {
  const { attractions, loading, error, refetch } = useAttractions();
  const navigate = useNavigate();

  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('all');
  const [cityFilter, setCityFilter] = useState('');

  const filtered = filterAttractions(attractions, { search, category, city: cityFilter });

  // Unique cities for quick filter
  const cities = [...new Set(attractions.map((a) => a.city))].slice(0, 8);

  return (
    <div className="alp-page">
      <header className="alp-header">
        <h1 className="alp-title">Explore Attractions</h1>
        <p className="alp-sub">Discover monuments, temples, parks & more</p>

        <div className="alp-search-wrap">
          <input
            className="alp-search"
            type="text"
            placeholder="Search attractions or cities..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <span className="alp-search-icon">🔍</span>
        </div>
      </header>

      <div className="alp-body">
        {/* Category Filter */}
        <div className="alp-filters">
          <CategoryFilter selected={category} onChange={setCategory} />
        </div>

        {/* City Quick Filter */}
        {cities.length > 0 && (
          <div className="alp-cities">
            <button
              className={`alp-city-btn ${!cityFilter ? 'active' : ''}`}
              onClick={() => setCityFilter('')}
            >All Cities</button>
            {cities.map((city) => (
              <button
                key={city}
                className={`alp-city-btn ${cityFilter === city ? 'active' : ''}`}
                onClick={() => setCityFilter(cityFilter === city ? '' : city)}
              >
                {city}
              </button>
            ))}
          </div>
        )}

        {/* Results count */}
        {!loading && (
          <p className="alp-count">
            {filtered.length} attraction{filtered.length !== 1 ? 's' : ''} found
          </p>
        )}

        {/* Loading skeletons */}
        {loading && (
          <div className="alp-grid">
            {[1,2,3,4,5,6].map((i) => <div key={i} className="alp-skeleton" />)}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="alp-error">
            <p>⚠ {error}</p>
            <button onClick={refetch}>Retry</button>
          </div>
        )}

        {/* Empty */}
        {!loading && !error && filtered.length === 0 && (
          <div className="alp-empty">
            <p>🗺️ No attractions found.</p>
            <p>Try a different filter or search term.</p>
          </div>
        )}

        {/* Grid */}
        {!loading && !error && filtered.length > 0 && (
          <div className="alp-grid">
            {filtered.map((a) => (
              <AttractionCard
                key={a.id}
                attraction={a}
                onSelect={(attr) => navigate(`/attractions/${attr.id}`)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AttractionsListPage;
