import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './RegisterAttractionPage.css';

const RegisterAttractionPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const [form, setForm] = useState({
    name: '',
    category: 'monument',
    description: '',
    address: '',
    city: '',
    is_free: true,
    entry_fee: '',
  });

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm({ ...form, [name]: type === 'checkbox' ? checked : value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => {
      setSuccess(true);
      setTimeout(() => navigate('/attractions'), 2000);
    }, 1500);
  };

  if (success) {
    return (
      <div className="rap-page success">
        <div className="rap-card">
          <div className="rap-success-icon">🏛️</div>
          <h2>Attraction Submitted!</h2>
          <p>Thank you for contributing to Yatrip. We will verify your entry soon.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="rap-page">
      <div className="rap-container">
        <header className="rap-header">
          <button className="rap-back" onClick={() => navigate('/attractions')}>← Back</button>
          <h1>Register a New Attraction</h1>
          <p>Add a monument, temple, or park to our map</p>
        </header>

        <form className="rap-card" onSubmit={handleSubmit}>
          <div className="rap-section">
            <h3>🏛 Basic Info</h3>
            <div className="rap-field">
              <label>Name of the Attraction *</label>
              <input name="name" value={form.name} onChange={handleChange} placeholder="e.g. Amber Fort" required />
            </div>

            <div className="rap-field">
              <label>Category</label>
              <select name="category" value={form.category} onChange={handleChange}>
                <option value="monument">Monument</option>
                <option value="temple">Temple/Religious</option>
                <option value="park">Park/Nature</option>
                <option value="museum">Museum</option>
              </select>
            </div>
          </div>

          <div className="rap-section">
            <h3>📍 Location & Access</h3>
            <div className="rap-field">
              <label>Address *</label>
              <input name="address" value={form.address} onChange={handleChange} placeholder="Street, Area..." required />
            </div>
            <div className="rap-field">
              <label>City *</label>
              <input name="city" value={form.city} onChange={handleChange} placeholder="e.g. Jaipur" required />
            </div>

            <div className="rap-row">
              <div className="rap-field">
                <label>Entry Type</label>
                <div className="rap-toggle">
                  <input type="checkbox" name="is_free" checked={form.is_free} onChange={handleChange} />
                  <span>{form.is_free ? 'Free Entry' : 'Paid Entry'}</span>
                </div>
              </div>
              {!form.is_free && (
                <div className="rap-field">
                  <label>Entry Fee (₹)</label>
                  <input type="number" name="entry_fee" value={form.entry_fee} onChange={handleChange} placeholder="100" />
                </div>
              )}
            </div>
          </div>

          <div className="rap-field">
            <label>Short Description</label>
            <textarea name="description" value={form.description} onChange={handleChange} placeholder="Historical significance or visitor tips..." rows="3" />
          </div>

          <button type="submit" className="rap-submit-btn" disabled={loading}>
            {loading ? 'Submitting...' : 'Add Attraction'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default RegisterAttractionPage;
