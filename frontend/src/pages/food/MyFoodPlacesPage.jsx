import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './MyFoodPlacesPage.css';

const MyFoodPlacesPage = () => {
  const navigate = useNavigate();
  const [places, setPlaces] = useState([]); // In a real app, fetch from API

  return (
    <div className="mfp-page">
      <div className="mfp-container">
        <header className="mfp-header">
          <div className="mfp-header-left">
            <button className="mfp-back" onClick={() => navigate('/food')}>← Back</button>
            <h1>My Food Outlets</h1>
            <p>Manage your restaurants, cafes, and dhabas</p>
          </div>
          <button className="mfp-add-btn" onClick={() => navigate('/register-food')}>
            + Register New Outlet
          </button>
        </header>

        {places.length === 0 ? (
          <div className="mfp-empty">
            <div className="mfp-empty-icon">🍽️</div>
            <h3>No outlets registered yet</h3>
            <p>Ready to serve travelers? Register your restaurant today!</p>
            <button className="mfp-primary-btn" onClick={() => navigate('/register-food')}>
              Get Started
            </button>
          </div>
        ) : (
          <div className="mfp-grid">
            {/* Map through places here */}
          </div>
        )}
      </div>
    </div>
  );
};

export default MyFoodPlacesPage;
