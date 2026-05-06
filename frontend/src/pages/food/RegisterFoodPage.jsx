import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './RegisterFoodPage.css';

const RegisterFoodPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const [form, setForm] = useState({
    name: '',
    category: 'restaurant',
    cuisine: 'multi',
    description: '',
    address: '',
    city: '',
    price_level: 2,
    avg_cost_for_two: '',
    is_veg: true,
  });

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm({ ...form, [name]: type === 'checkbox' ? checked : value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    // Simulation for now, or use a foodService if available
    setTimeout(() => {
      setSuccess(true);
      setTimeout(() => navigate('/food'), 2000);
    }, 1500);
  };

  if (success) {
    return (
      <div className="rfp-page success">
        <div className="rfp-card">
          <div className="rfp-success-icon">🥘</div>
          <h2>Restaurant Registered!</h2>
          <p>Your food place is now live on Yatrip Food.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="rfp-page">
      <div className="rfp-container">
        <header className="rfp-header">
          <button className="rfp-back" onClick={() => navigate('/food')}>← Back</button>
          <h1>Register Your Food Business</h1>
          <p>Join Yatrip Food and reach hungry travelers nearby</p>
        </header>

        <form className="rfp-card" onSubmit={handleSubmit}>
          <div className="rfp-section">
            <h3>🍽 Basic Details</h3>
            <div className="rfp-field">
              <label>Outlet Name *</label>
              <input name="name" value={form.name} onChange={handleChange} placeholder="e.g. Royal Punjabi Dhaba" required />
            </div>

            <div className="rfp-row">
              <div className="rfp-field">
                <label>Category</label>
                <select name="category" value={form.category} onChange={handleChange}>
                  <option value="restaurant">Restaurant</option>
                  <option value="cafe">Café</option>
                  <option value="dhaba">Dhaba</option>
                  <option value="street_food">Street Food</option>
                </select>
              </div>
              <div className="rfp-field">
                <label>Cuisine Type</label>
                <select name="cuisine" value={form.cuisine} onChange={handleChange}>
                  <option value="north_indian">North Indian</option>
                  <option value="south_indian">South Indian</option>
                  <option value="chinese">Chinese</option>
                  <option value="multi">Multi-Cuisine</option>
                </select>
              </div>
            </div>
          </div>

          <div className="rfp-section">
            <h3>📍 Location & Pricing</h3>
            <div className="rfp-field">
              <label>Full Address *</label>
              <input name="address" value={form.address} onChange={handleChange} placeholder="Shop no, Building, Street..." required />
            </div>
            <div className="rfp-field">
              <label>City *</label>
              <input name="city" value={form.city} onChange={handleChange} placeholder="e.g. Jaipur" required />
            </div>

            <div className="rfp-row">
              <div className="rfp-field">
                <label>Avg. Cost for Two (₹)</label>
                <input type="number" name="avg_cost_for_two" value={form.avg_cost_for_two} onChange={handleChange} placeholder="500" />
              </div>
              <div className="rfp-field">
                <label>Vegetarian Only?</label>
                <div className="rfp-toggle">
                  <input type="checkbox" name="is_veg" checked={form.is_veg} onChange={handleChange} />
                  <span>{form.is_veg ? 'Yes (Pure Veg)' : 'No (Non-Veg available)'}</span>
                </div>
              </div>
            </div>
          </div>

          <button type="submit" className="rfp-submit-btn" disabled={loading}>
            {loading ? 'Processing...' : 'Register My Outlet'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default RegisterFoodPage;
