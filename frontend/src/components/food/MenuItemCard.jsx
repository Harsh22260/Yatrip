import React from 'react';
import { formatPrice } from '../../utils/foodHelpers';
import './MenuItemCard.css';

const MenuItemCard = ({ item }) => {
  return (
    <div className={`mic-card ${!item.is_available ? 'unavailable' : ''}`}>
      <div className="mic-left">
        {item.image ? (
          <img src={item.image} alt={item.name} className="mic-image" />
        ) : (
          <div className="mic-placeholder">🍽️</div>
        )}
      </div>
      <div className="mic-body">
        <div className="mic-header">
          <h4 className="mic-name">{item.name}</h4>
          {!item.is_available && (
            <span className="mic-unavail">Unavailable</span>
          )}
        </div>
        {item.description && (
          <p className="mic-desc">{item.description}</p>
        )}
        <span className="mic-price">{formatPrice(item.price)}</span>
      </div>
    </div>
  );
};

export default MenuItemCard;
