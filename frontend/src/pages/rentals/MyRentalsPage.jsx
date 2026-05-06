import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchMyRentals } from '../../services/rentalService';
import RentalCard from '../../components/rentals/RentalCard';
import './MyRentalsPage.css';

const MyRentalsPage = () => {
  const [rentals, setRentals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetchMyRentals()
      .then(setRentals)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mrp-page">
      <div className="mrp-container">
        <header className="mrp-header">
          <div className="mrp-header-left">
            <button className="mrp-back" onClick={() => navigate('/rentals')}>← Back</button>
            <h1>My Listed Properties</h1>
            <p>Manage your homestays, PGs, and hostels</p>
          </div>
          <button className="mrp-add-btn" onClick={() => navigate('/register-rental')}>
            + Add New Property
          </button>
        </header>

        {loading && <div className="mrp-loading">Loading your listings...</div>}
        {error && <div className="mrp-error">⚠ {error}</div>}

        {!loading && !error && rentals.length === 0 && (
          <div className="mrp-empty">
            <div className="mrp-empty-icon">🏠</div>
            <h3>No properties listed yet</h3>
            <p>Start earning by listing your spare rooms or property today!</p>
            <button className="mrp-primary-btn" onClick={() => navigate('/register-rental')}>
              List My First Property
            </button>
          </div>
        )}

        <div className="mrp-grid">
          {rentals.map(rental => (
            <div key={rental.id} className="mrp-card-wrap">
              <RentalCard rental={rental} onSelect={(r) => navigate(`/rentals/${r.id}`)} />
              <div className="mrp-card-footer">
                <button className="mrp-edit-btn" onClick={() => navigate(`/rentals/${rental.id}/edit`)}>Edit</button>
                <div className="mrp-status-tag">
                  {rental.is_verified ? '✅ Verified' : '⏳ Pending Verification'}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default MyRentalsPage;
