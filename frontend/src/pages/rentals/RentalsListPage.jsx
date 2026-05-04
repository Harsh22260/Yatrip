import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useRentals, useAmenities } from '../../hooks/useRentals';
import RentalCard from '../../components/rentals/RentalCard';
import RentalFilters from '../../components/rentals/RentalFilters';
import { filterRentals } from '../../utils/rentalHelpers';
import './RentalsListPage.css';

const SORT_OPTIONS = [
  { value: 'newest', label: '🕐 Newest' },
  { value: 'price_asc', label: '💰 Price: Low' },
  { value: 'price_desc', label: '💰 Price: High' },
  { value: 'rooms', label: '🛏 Most Rooms' },
];

const sortRentals = (rentals, sort) => {
  const r = [...rentals];
  if (sort === 'price_asc') return r.sort((a, b) => parseFloat(a.price_per_month) - parseFloat(b.price_per_month));
  if (sort === 'price_desc') return r.sort((a, b) => parseFloat(b.price_per_month) - parseFloat(a.price_per_month));
  if (sort === 'rooms') return r.sort((a, b) => b.available_rooms - a.available_rooms);
  return r;
};

const DEFAULT_FILTERS = { search: '', type: 'all', maxPrice: '', minRooms: '', selectedAmenities: [] };

const RentalsListPage = () => {
  const { rentals, loading, error, refetch } = useRentals();
  const { amenities } = useAmenities();
  const navigate = useNavigate();

  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [sort, setSort] = useState('newest');
  const [viewMode, setViewMode] = useState('grid'); // grid | list
  const [showFilters, setShowFilters] = useState(true);

  const filtered = filterRentals(rentals, {
    search: filters.search,
    type: filters.type,
    maxPrice: filters.maxPrice,
    minRooms: filters.minRooms,
    amenities: filters.selectedAmenities,
  });

  const sorted = sortRentals(filtered, sort);

  return (
    <div className="rlp-page">
      {/* Header */}
      <header className="rlp-header">
        <div className="rlp-header-content">
          <div>
            <h1 className="rlp-title">Find Your Perfect Stay</h1>
            <p className="rlp-sub">Homestays, PGs & Hostels — verified & affordable</p>
          </div>
          <div className="rlp-header-stats">
            <div className="rlp-stat">
              <span className="rlp-stat-num">{rentals.length}</span>
              <span className="rlp-stat-label">Listings</span>
            </div>
          </div>
        </div>
      </header>

      <div className="rlp-layout">
        {/* Sidebar Filters */}
        <div className={`rlp-filter-col ${showFilters ? 'visible' : 'hidden'}`}>
          <RentalFilters
            filters={filters}
            onChange={setFilters}
            amenities={amenities}
            totalCount={rentals.length}
            filteredCount={filtered.length}
            onReset={() => setFilters(DEFAULT_FILTERS)}
          />
        </div>

        {/* Main Content */}
        <div className="rlp-main">
          {/* Toolbar */}
          <div className="rlp-toolbar">
            <button className="rlp-filter-toggle" onClick={() => setShowFilters(!showFilters)}>
              {showFilters ? '◀ Hide Filters' : '▶ Show Filters'}
            </button>

            <span className="rlp-result-count">
              {loading ? '...' : `${sorted.length} rental${sorted.length !== 1 ? 's' : ''}`}
            </span>

            <div className="rlp-toolbar-right">
              <select className="rlp-sort" value={sort} onChange={(e) => setSort(e.target.value)}>
                {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>

              <div className="rlp-view-toggle">
                <button className={`rlp-view-btn ${viewMode === 'grid' ? 'active' : ''}`} onClick={() => setViewMode('grid')}>⊞</button>
                <button className={`rlp-view-btn ${viewMode === 'list' ? 'active' : ''}`} onClick={() => setViewMode('list')}>☰</button>
              </div>
            </div>
          </div>

          {/* Loading */}
          {loading && (
            <div className={`rlp-${viewMode}`}>
              {[1,2,3,4,5,6].map((i) => <div key={i} className="rlp-skeleton" />)}
            </div>
          )}

          {error && (
            <div className="rlp-error">⚠ {error} <button onClick={refetch}>Retry</button></div>
          )}

          {!loading && !error && sorted.length === 0 && (
            <div className="rlp-empty">
              <p>🏠 No rentals match your filters.</p>
              <button onClick={() => setFilters(DEFAULT_FILTERS)}>Clear Filters</button>
            </div>
          )}

          {!loading && !error && sorted.length > 0 && (
            <div className={`rlp-${viewMode}`}>
              {sorted.map((rental) => (
                <RentalCard
                  key={rental.id}
                  rental={rental}
                  onSelect={(r) => navigate(`/rentals/${r.id}`)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RentalsListPage;
