import React from 'react';
import { ALL_RENTAL_TYPES, getRentalTypeMeta } from '../../utils/rentalHelpers';
import './RentalFilters.css';

const RentalFilters = ({
  filters,
  onChange,
  amenities = [],
  totalCount,
  filteredCount,
  onReset,
}) => {
  const { search, type, maxPrice, minRooms, selectedAmenities = [] } = filters;

  const toggleAmenity = (name) => {
    const updated = selectedAmenities.includes(name)
      ? selectedAmenities.filter((a) => a !== name)
      : [...selectedAmenities, name];
    onChange({ ...filters, selectedAmenities: updated });
  };

  const hasActiveFilters =
    type !== 'all' || maxPrice || minRooms || selectedAmenities.length > 0;

  return (
    <aside className="rf-sidebar">
      <div className="rf-header">
        <h3 className="rf-title">🔍 Filters</h3>
        {hasActiveFilters && (
          <button className="rf-reset" onClick={onReset}>Reset all</button>
        )}
      </div>

      <p className="rf-count">
        <span className="rf-count-num">{filteredCount}</span> of {totalCount} rentals
      </p>

      {/* Search */}
      <div className="rf-section">
        <label className="rf-label">Search</label>
        <div className="rf-search-wrap">
          <input
            className="rf-search"
            type="text"
            placeholder="Name or area..."
            value={search}
            onChange={(e) => onChange({ ...filters, search: e.target.value })}
          />
          <span>🔍</span>
        </div>
      </div>

      {/* Type */}
      <div className="rf-section">
        <label className="rf-label">Type</label>
        <div className="rf-type-grid">
          {ALL_RENTAL_TYPES.map((t) => {
            const meta = t === 'all' ? { icon: '🏠', label: 'All', color: '#6b7280' } : getRentalTypeMeta(t);
            return (
              <button
                key={t}
                className={`rf-type-btn ${type === t ? 'active' : ''}`}
                style={type === t ? { background: meta.color, borderColor: meta.color } : {}}
                onClick={() => onChange({ ...filters, type: t })}
              >
                <span>{meta.icon}</span>
                <span>{meta.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Max Price */}
      <div className="rf-section">
        <label className="rf-label">
          Max Price: <strong>{maxPrice ? `₹${Number(maxPrice).toLocaleString('en-IN')}` : 'Any'}</strong>
        </label>
        <input
          type="range"
          min="2000"
          max="50000"
          step="1000"
          value={maxPrice || 50000}
          onChange={(e) => onChange({ ...filters, maxPrice: e.target.value === '50000' ? '' : e.target.value })}
          className="rf-range"
        />
        <div className="rf-range-labels">
          <span>₹2,000</span>
          <span>₹50,000</span>
        </div>
      </div>

      {/* Min Rooms */}
      <div className="rf-section">
        <label className="rf-label">Min Available Rooms</label>
        <div className="rf-rooms-btns">
          {['', '1', '2', '3', '5'].map((n) => (
            <button
              key={n}
              className={`rf-room-btn ${minRooms === n ? 'active' : ''}`}
              onClick={() => onChange({ ...filters, minRooms: n })}
            >
              {n === '' ? 'Any' : `${n}+`}
            </button>
          ))}
        </div>
      </div>

      {/* Amenities */}
      {amenities.length > 0 && (
        <div className="rf-section">
          <label className="rf-label">Amenities</label>
          <div className="rf-amenities-grid">
            {amenities.map((a) => (
              <button
                key={a.id}
                className={`rf-amenity-btn ${selectedAmenities.includes(a.name) ? 'active' : ''}`}
                onClick={() => toggleAmenity(a.name)}
              >
                {a.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </aside>
  );
};

export default RentalFilters;
