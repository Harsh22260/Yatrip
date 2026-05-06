import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { createRental, fetchAmenities } from '../../services/rentalService';
import './RegisterRentalPage.css';

const RegisterRentalPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [allAmenities, setAllAmenities] = useState([]);
  const [success, setSuccess] = useState(false);

  const [form, setForm] = useState({
    name: '',
    rental_type: 'homestay',
    description: '',
    address: '',
    price_per_month: '',
    available_rooms: 1,
    selectedAmenities: [],
  });

  useEffect(() => {
    fetchAmenities().then(setAllAmenities).catch(console.error);
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm({ ...form, [name]: value });
  };

  const toggleAmenity = (id) => {
    const updated = form.selectedAmenities.includes(id)
      ? form.selectedAmenities.filter(a => a !== id)
      : [...form.selectedAmenities, id];
    setForm({ ...form, selectedAmenities: updated });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name || !form.address || !form.price_per_month) {
      setError('Please fill in all required fields.');
      return;
    }

    setLoading(true);
    setError('');
    try {
      await createRental({
        ...form,
        amenities: form.selectedAmenities
      });
      setSuccess(true);
      setTimeout(() => navigate('/rentals'), 2000);
    } catch (err) {
      setError(err.message || 'Failed to register rental');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="rrp-page success">
        <div className="rrp-card">
          <div className="rrp-success-icon">✅</div>
          <h2>Rental Registered Successfully!</h2>
          <p>Your property is now being listed. Redirecting...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="rrp-page">
      <div className="rrp-container">
        <header className="rrp-header">
          <button className="rrp-back" onClick={() => navigate('/rentals')}>← Back</button>
          <h1>Register Your Property</h1>
          <p>Homestays, PGs, or Hostels — list your space today</p>
        </header>

        <form className="rrp-card" onSubmit={handleSubmit}>
          {error && <div className="rrp-error">{error}</div>}

          <div className="rrp-section">
            <h3>🏠 Basic Information</h3>
            <div className="rrp-field">
              <label>Property Name *</label>
              <input name="name" value={form.name} onChange={handleChange} placeholder="e.g. Sunshine Homestay" />
            </div>

            <div className="rrp-row">
              <div className="rrp-field">
                <label>Property Type *</label>
                <select name="rental_type" value={form.rental_type} onChange={handleChange}>
                  <option value="homestay">Homestay</option>
                  <option value="pg">Paying Guest (PG)</option>
                  <option value="hostel">Hostel</option>
                </select>
              </div>
              <div className="rrp-field">
                <label>Monthly Rent (₹) *</label>
                <input type="number" name="price_per_month" value={form.price_per_month} onChange={handleChange} placeholder="8000" />
              </div>
            </div>

            <div className="rrp-field">
              <label>Address *</label>
              <input name="address" value={form.address} onChange={handleChange} placeholder="Full address" />
            </div>

            <div className="rrp-field">
              <label>Available Rooms</label>
              <input type="number" name="available_rooms" value={form.available_rooms} min="1" onChange={handleChange} />
            </div>

            <div className="rrp-field">
              <label>Description</label>
              <textarea name="description" value={form.description} onChange={handleChange} placeholder="Tell us more about the property..." rows="3" />
            </div>
          </div>

          <div className="rrp-section">
            <h3>✨ Amenities</h3>
            <div className="rrp-amenities-grid">
              {allAmenities.map(amenity => (
                <label key={amenity.id} className={`rrp-amenity-pill ${form.selectedAmenities.includes(amenity.id) ? 'active' : ''}`}>
                  <input type="checkbox" checked={form.selectedAmenities.includes(amenity.id)} onChange={() => toggleAmenity(amenity.id)} />
                  {amenity.name}
                </label>
              ))}
            </div>
          </div>

          <button type="submit" className="rrp-submit-btn" disabled={loading}>
            {loading ? 'Registering...' : 'List My Property'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default RegisterRentalPage;
