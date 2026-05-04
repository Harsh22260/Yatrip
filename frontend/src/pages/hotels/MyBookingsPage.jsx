import React, { useState } from 'react';
import { useMyBookings } from "../../hooks/useHotels";
import { cancelBooking, confirmBooking } from "../../services/hotelService";
import BookingStatusBadge from "../../components/hotels/BookingStatusBadge";
import { formatDate, formatPrice, calcNights, getHoldSecondsLeft } from "../../utils/hotelHelpers";
import './MyBookingsPage.css';


const HoldTimer = ({ expiresAt }) => {
  const [secs, setSecs] = React.useState(getHoldSecondsLeft(expiresAt));
  React.useEffect(() => {
    const t = setInterval(() => setSecs(getHoldSecondsLeft(expiresAt)), 1000);
    return () => clearInterval(t);
  }, [expiresAt]);
  const m = String(Math.floor(secs / 60)).padStart(2, '0');
  const s = String(secs % 60).padStart(2, '0');
  return <span className={`mbp-timer ${secs < 60 ? 'urgent' : ''}`}>⏳ {m}:{s}</span>;
};

const MyBookingsPage = () => {
  const { bookings, loading, error, refetch } = useMyBookings();
  const [actionLoading, setActionLoading] = useState(null);

  const handleCancel = async (id) => {
    if (!window.confirm('Cancel this booking?')) return;
    setActionLoading(id);
    try {
      await cancelBooking(id);
      refetch();
    } catch (e) {
      alert(e.message);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="mbp-page">
      <header className="mbp-header">
        <h1 className="mbp-title">My Bookings</h1>
        <p className="mbp-sub">{bookings.length} booking{bookings.length !== 1 ? 's' : ''} found</p>
      </header>

      <div className="mbp-body">
        {loading && <div className="mbp-loading">Loading bookings...</div>}
        {error && <div className="mbp-error">⚠ {error}</div>}

        {!loading && bookings.length === 0 && (
          <div className="mbp-empty">
            <p>🏨 No bookings yet.</p>
            <p>Start exploring hotels!</p>
          </div>
        )}

        <div className="mbp-list">
          {bookings.map((b) => {
            const nights = calcNights(b.check_in, b.check_out);
            return (
              <div key={b.id} className="mbp-card">
                <div className="mbp-card-top">
                  <div>
                    <h3 className="mbp-hotel-name">{b.hotel?.name || `Hotel #${b.hotel}`}</h3>
                    <p className="mbp-room">{b.room_type?.name || `Room Type #${b.room_type}`}</p>
                  </div>
                  <BookingStatusBadge status={b.status} />
                </div>

                <div className="mbp-dates">
                  <span>📅 {formatDate(b.check_in)} → {formatDate(b.check_out)}</span>
                  <span className="mbp-nights">{nights} night{nights > 1 ? 's' : ''}</span>
                </div>

                <div className="mbp-card-footer">
                  <span className="mbp-price">{formatPrice(b.total_price)}</span>

                  {b.status === 'HELD' && b.hold_expires_at && (
                    <HoldTimer expiresAt={b.hold_expires_at} />
                  )}

                  <div className="mbp-actions">
                    {(b.status === 'HELD' || b.status === 'CONFIRMED') && (
                      <button
                        className="mbp-btn cancel"
                        onClick={() => handleCancel(b.id)}
                        disabled={actionLoading === b.id}
                      >
                        {actionLoading === b.id ? '...' : 'Cancel'}
                      </button>
                    )}
                  </div>
                </div>

                <p className="mbp-id">ID: {b.id}</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default MyBookingsPage;
