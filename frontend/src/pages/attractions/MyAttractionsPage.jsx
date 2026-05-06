import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './MyAttractionsPage.css';

const MyAttractionsPage = () => {
  const navigate = useNavigate();
  const [attractions, setAttractions] = useState([]);

  return (
    <div className="map-page">
      <div className="map-container">
        <header className="map-header">
          <div className="map-header-left">
            <button className="map-back" onClick={() => navigate('/attractions')}>← Back</button>
            <h1>My Attractions</h1>
            <p>Manage the places you've added to Yatrip</p>
          </div>
          <button className="map-add-btn" onClick={() => navigate('/register-attraction')}>
            + Add New Attraction
          </button>
        </header>

        {attractions.length === 0 ? (
          <div className="map-empty">
            <div className="map-empty-icon">📍</div>
            <h3>No attractions added yet</h3>
            <p>Help other travelers by adding interesting places nearby!</p>
            <button className="map-primary-btn" onClick={() => navigate('/register-attraction')}>
              Add First Place
            </button>
          </div>
        ) : (
          <div className="map-grid">
            {/* Map through attractions here */}
          </div>
        )}
      </div>
    </div>
  );
};

export default MyAttractionsPage;
