import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createHotel, createRoomType } from '../../services/hotelService';
import './RegisterHotelPage.css';

const STEPS = ['Hotel Info', 'Room Types', 'Done'];

const RegisterHotelPage = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [createdHotel, setCreatedHotel] = useState(null);

  // Step 1: Hotel form
  const [hotelForm, setHotelForm] = useState({
    name: '',
    description: '',
    address: '',
    rating: 3.0,
  });

  // Step 2: Room types
  const [rooms, setRooms] = useState([
    { name: '', description: '', capacity: 2, base_price: '', total_units: 1 }
  ]);

  const handleHotelChange = (e) => {
    setHotelForm({ ...hotelForm, [e.target.name]: e.target.value });
  };

  const handleRoomChange = (idx, field, value) => {
    const updated = [...rooms];
    updated[idx][field] = value;
    setRooms(updated);
  };

  const addRoom = () => {
    setRooms([...rooms, { name: '', description: '', capacity: 2, base_price: '', total_units: 1 }]);
  };

  const removeRoom = (idx) => {
    if (rooms.length === 1) return;
    setRooms(rooms.filter((_, i) => i !== idx));
  };

  const handleHotelSubmit = async () => {
    if (!hotelForm.name || !hotelForm.address) {
      setError('Hotel name aur address required hai.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const hotel = await createHotel(hotelForm);
      setCreatedHotel(hotel);
      setStep(1);
    } catch (e) {
      setError('Hotel create failed: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRoomsSubmit = async () => {
    const validRooms = rooms.filter(r => r.name && r.base_price);
    if (validRooms.length === 0) {
      setError('Kam se kam ek room type add karo.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      for (const room of validRooms) {
        await createRoomType({ ...room, hotel: createdHotel.id });
      }
      setStep(2);
    } catch (e) {
      setError('Room type save failed: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  const skipRooms = () => setStep(2);

  return (
    <div className="rhp-page">
      <div className="rhp-container">

        {/* Header */}
        <div className="rhp-header">
          <button className="rhp-back" onClick={() => navigate('/hotels')}>← Back</button>
          <h1 className="rhp-title">Register Your Hotel</h1>
          <p className="rhp-sub">List your property on Yatrip and reach thousands of travelers</p>
        </div>

        {/* Steps */}
        <div className="rhp-steps">
          {STEPS.map((s, i) => (
            <div key={s} className={`rhp-step ${i === step ? 'active' : ''} ${i < step ? 'done' : ''}`}>
              <div className="rhp-step-dot">{i < step ? '✓' : i + 1}</div>
              <span>{s}</span>
            </div>
          ))}
        </div>

        {/* Error */}
        {error && <div className="rhp-error">{error}</div>}

        {/* ── STEP 0: Hotel Info ── */}
        {step === 0 && (
          <div className="rhp-card">
            <h2 className="rhp-card-title">🏨 Hotel Details</h2>

            <div className="rhp-field">
              <label>Hotel Name *</label>
              <input
                name="name"
                value={hotelForm.name}
                onChange={handleHotelChange}
                placeholder="e.g. The Grand Yatrip Palace"
              />
            </div>

            <div className="rhp-field">
              <label>Address *</label>
              <input
                name="address"
                value={hotelForm.address}
                onChange={handleHotelChange}
                placeholder="Full address including city & state"
              />
            </div>

            <div className="rhp-field">
              <label>Description</label>
              <textarea
                name="description"
                value={hotelForm.description}
                onChange={handleHotelChange}
                placeholder="Tell travelers what makes your hotel special..."
                rows={4}
              />
            </div>

            <div className="rhp-field">
              <label>Rating (1–5)</label>
              <div className="rhp-rating-wrap">
                {[1, 2, 3, 4, 5].map((r) => (
                  <button
                    key={r}
                    className={`rhp-star-btn ${parseFloat(hotelForm.rating) >= r ? 'lit' : ''}`}
                    onClick={() => setHotelForm({ ...hotelForm, rating: r })}
                  >★</button>
                ))}
                <span className="rhp-rating-val">{hotelForm.rating}/5</span>
              </div>
            </div>

            <button
              className="rhp-btn primary"
              onClick={handleHotelSubmit}
              disabled={loading}
            >
              {loading ? 'Saving...' : 'Continue → Add Rooms'}
            </button>
          </div>
        )}

        {/* ── STEP 1: Room Types ── */}
        {step === 1 && (
          <div className="rhp-card">
            <h2 className="rhp-card-title">🛏 Room Types</h2>
            <p className="rhp-hint">Add different room types with pricing. You can add more later.</p>

            {rooms.map((room, idx) => (
              <div key={idx} className="rhp-room-block">
                <div className="rhp-room-header">
                  <span>Room Type {idx + 1}</span>
                  {rooms.length > 1 && (
                    <button className="rhp-remove-room" onClick={() => removeRoom(idx)}>✕ Remove</button>
                  )}
                </div>

                <div className="rhp-row-2">
                  <div className="rhp-field">
                    <label>Room Name *</label>
                    <input
                      value={room.name}
                      onChange={(e) => handleRoomChange(idx, 'name', e.target.value)}
                      placeholder="e.g. Deluxe Double"
                    />
                  </div>
                  <div className="rhp-field">
                    <label>Price/Night (₹) *</label>
                    <input
                      type="number"
                      value={room.base_price}
                      onChange={(e) => handleRoomChange(idx, 'base_price', e.target.value)}
                      placeholder="2500"
                    />
                  </div>
                </div>

                <div className="rhp-row-2">
                  <div className="rhp-field">
                    <label>Capacity (guests)</label>
                    <input
                      type="number"
                      value={room.capacity}
                      min={1}
                      onChange={(e) => handleRoomChange(idx, 'capacity', e.target.value)}
                    />
                  </div>
                  <div className="rhp-field">
                    <label>Total Units</label>
                    <input
                      type="number"
                      value={room.total_units}
                      min={1}
                      onChange={(e) => handleRoomChange(idx, 'total_units', e.target.value)}
                    />
                  </div>
                </div>

                <div className="rhp-field">
                  <label>Description</label>
                  <input
                    value={room.description}
                    onChange={(e) => handleRoomChange(idx, 'description', e.target.value)}
                    placeholder="e.g. King bed, AC, city view"
                  />
                </div>
              </div>
            ))}

            <button className="rhp-btn outline" onClick={addRoom}>+ Add Another Room Type</button>

            <div className="rhp-row-2" style={{ marginTop: '20px' }}>
              <button className="rhp-btn secondary" onClick={skipRooms}>Skip for Now</button>
              <button className="rhp-btn primary" onClick={handleRoomsSubmit} disabled={loading}>
                {loading ? 'Saving...' : 'Save Rooms →'}
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 2: Done ── */}
        {step === 2 && (
          <div className="rhp-card rhp-done">
            <div className="rhp-done-icon">🎉</div>
            <h2>Hotel Registered!</h2>
            <p>
              <strong>{createdHotel?.name}</strong> is now listed on Yatrip.
              Our team will verify it within 24–48 hours.
            </p>
            <div className="rhp-done-actions">
              <button className="rhp-btn secondary" onClick={() => navigate('/my-hotels')}>
                View My Hotels
              </button>
              <button className="rhp-btn primary" onClick={() => navigate('/hotels')}>
                Browse Hotels
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default RegisterHotelPage;