import React from 'react';
import { CATEGORIES, getCategoryMeta } from '../../utils/attractionHelpers';
import './CategoryFilter.css';

const CategoryFilter = ({ selected, onChange }) => {
  return (
    <div className="cf-wrap">
      {CATEGORIES.map((cat) => {
        const { icon, label } = cat === 'all'
          ? { icon: '🗺️', label: 'All' }
          : getCategoryMeta(cat);
        return (
          <button
            key={cat}
            className={`cf-btn ${selected === cat ? 'active' : ''}`}
            onClick={() => onChange(cat)}
          >
            <span className="cf-icon">{icon}</span>
            <span className="cf-label">{label}</span>
          </button>
        );
      })}
    </div>
  );
};

export default CategoryFilter;
