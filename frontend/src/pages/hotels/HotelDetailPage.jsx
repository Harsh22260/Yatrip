import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useHotelDetail, useRoomTypes } from "../../hooks/useHotels";
import RoomTypeCard from "../../components/hotels/RoomTypeCard";
import BookingModal from "../../components/hotels/BookingModal";
import { formatDate } from "../../utils/hotelHelpers";
import './HotelDetailPage.css';

const HotelDetailPage = () => {
  const { id: hotelId } = useParams();
  const navigate = useNavigate();
  const onBack = () => navigate('/hotels');

  const { hotel, loading, error } = useHotelDetail(hotelId);
  const { roomTypes, loading: roomsLoading } = useRoomTypes(hotelId);

  const [checkIn, setCheckIn] = useState('');
  const [checkOut, setCheckOut] = useState('');
  const [bookingData, setBookingData] = useState(null);

  const today = new Date().toISOString().split('T')[0];

  const handleBook = ({ room, ratePlan }) => {
    if (!checkIn || !checkOut) return;
    setBookingData({ room, ratePlan });
  };

  if (loading) return <div className="hdp-loading">Loading hotel...</div>;
  if (error) return <div className="hdp-error">⚠ {error} <button onClick={onBack}>← Back</button></div>;
  if (!hotel) return null;

  return (
    <div className="hdp-page">
      <div className="hdp-hero">
        <div className="hdp-hero-bg">🏨</div>
        <div className="hdp-hero-overlay">
          <button className="hdp-back-btn" onClick={onBack}>← All Hotels</button>
          <div className="hdp-hero-info">
            <div className="hdp-badges">
              {hotel.is_verified && <span className="hdp-badge verified">✓ Verified</span>}
              <span className="hdp-badge rating">★ {hotel.rating}</span>
            </div>
            <h1 className="hdp-hotel-name">{hotel.name}</h1>
            <p className="hdp-address">📍 {hotel.address}</p>
          </div>
        </div>
      </div>

      <div className="hdp-body">
        {hotel.description && (
          <section className="hdp-section">
            <h2 className="hdp-section-title">About</h2>
            <p className="hdp-description">{hotel.description}</p>
          </section>
        )}

        <section className="hdp-section hdp-dates-section">
          <h2 className="hdp-section-title">Select Dates</h2>
          <div className="hdp-dates">
            <label>
              <span>Check-in</span>
              <input
                type="date"
                value={checkIn}
                min={today}
                onChange={(e) => {
                  setCheckIn(e.target.value);
                  if (checkOut && e.target.value >= checkOut) setCheckOut('');
                }}
              />
            </label>
            <label>
              <span>Check-out</span>
              <input
                type="date"
                value={checkOut}
                min={checkIn || today}
                onChange={(e) => setCheckOut(e.target.value)}
              />
            </label>
          </div>
          {checkIn && checkOut && (
            <p className="hdp-date-summary">
              {formatDate(checkIn)} → {formatDate(checkOut)}
            </p>
          )}
        </section>

        <section className="hdp-section">
          <h2 className="hdp-section-title">Available Rooms</h2>
          {roomsLoading ? (
            <div className="hdp-rooms-loading">Loading rooms...</div>
          ) : roomTypes.length === 0 ? (
            <p className="hdp-no-rooms">No rooms found for this hotel.</p>
          ) : (
            <div className="hdp-rooms-grid">
              {roomTypes.map((room) => (
                <RoomTypeCard
                  key={room.id}
                  room={room}
                  checkIn={checkIn}
                  checkOut={checkOut}
                  onBook={handleBook}
                />
              ))}
            </div>
          )}
        </section>
      </div>

      {bookingData && (
        <BookingModal
          hotel={hotel}
          room={bookingData.room}
          ratePlan={bookingData.ratePlan}
          checkIn={checkIn}
          checkOut={checkOut}
          onClose={() => setBookingData(null)}
          onSuccess={() => setBookingData(null)}
        />
      )}
    </div>
  );
};

export default HotelDetailPage;
