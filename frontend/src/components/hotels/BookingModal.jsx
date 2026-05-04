import React, { useState, useEffect } from 'react';
import { formatPrice, formatDate, calcNights, getHoldSecondsLeft } from '../../utils/hotelHelpers';
import { createBooking, confirmBooking, cancelBooking } from '../../services/hotelService';
import './BookingModal.css';

const BookingModal = ({ hotel, room, ratePlan, checkIn, checkOut, onClose, onSuccess }) => {
  const [step, setStep] = useState('review'); // review | hold | confirmed | error
  const [booking, setBooking] = useState(null);
  const [holdToken, setHoldToken] = useState('');
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const nights = calcNights(checkIn, checkOut);
  const multiplier = ratePlan?.price_multiplier || 1;
  const total = parseFloat(room.base_price) * parseFloat(multiplier) * nights;

  // Countdown timer
  useEffect(() => {
    if (step !== 'hold' || !booking?.hold_expires_at) return;
    const tick = setInterval(() => {
      const left = getHoldSecondsLeft(booking.hold_expires_at);
      setSecondsLeft(left);
      if (left === 0) {
        clearInterval(tick);
        setStep('error');
        setErrorMsg('Hold expired. Please try again.');
      }
    }, 1000);
    return () => clearInterval(tick);
  }, [step, booking]);

  const handleHold = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await createBooking({
        hotel: hotel.id,
        room_type: room.id,
        room_unit: null,
        rate_plan: ratePlan?.id || null,
        check_in: checkIn,
        check_out: checkOut,
      });
      setBooking(res.booking);
      setHoldToken(res.hold_token);
      setSecondsLeft(getHoldSecondsLeft(res.expires_at));
      setStep('hold');
    } catch (e) {
      setErrorMsg(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await confirmBooking(booking.id, holdToken);
      setStep('confirmed');
      onSuccess?.();
    } catch (e) {
      setErrorMsg(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!booking) { onClose(); return; }
    setLoading(true);
    try {
      await cancelBooking(booking.id);
    } catch (_) {}
    setLoading(false);
    onClose();
  };

  const fmtTime = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

  return (
    <div className="bm-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="bm-modal">
        <button className="bm-close" onClick={onClose}>✕</button>

        {/* ─── STEP: REVIEW ─── */}
        {step === 'review' && (
          <>
            <h2 className="bm-title">Review Booking</h2>
            <div className="bm-hotel">{hotel.name}</div>

            <div className="bm-rows">
              <div className="bm-row"><span>Room</span><strong>{room.name}</strong></div>
              <div className="bm-row"><span>Check-in</span><strong>{formatDate(checkIn)}</strong></div>
              <div className="bm-row"><span>Check-out</span><strong>{formatDate(checkOut)}</strong></div>
              <div className="bm-row"><span>Nights</span><strong>{nights}</strong></div>
              {ratePlan && (
                <div className="bm-row">
                  <span>Rate Plan</span>
                  <strong>{ratePlan.name} {ratePlan.refundable ? '(Refundable)' : '(Non-refundable)'}</strong>
                </div>
              )}
              <div className="bm-row bm-total">
                <span>Total</span>
                <strong>{formatPrice(total)}</strong>
              </div>
            </div>

            <p className="bm-hold-info">⏳ Booking will be held for <strong>10 minutes</strong> after placing.</p>
            {errorMsg && <p className="bm-error">{errorMsg}</p>}

            <div className="bm-actions">
              <button className="bm-btn secondary" onClick={onClose}>Cancel</button>
              <button className="bm-btn primary" onClick={handleHold} disabled={loading}>
                {loading ? 'Placing Hold...' : 'Place Hold →'}
              </button>
            </div>
          </>
        )}

        {/* ─── STEP: HOLD ─── */}
        {step === 'hold' && (
          <>
            <h2 className="bm-title">Booking Held!</h2>
            <div className={`bm-timer ${secondsLeft < 60 ? 'urgent' : ''}`}>
              <span>{fmtTime(secondsLeft)}</span>
              <p>remaining to confirm</p>
            </div>

            <div className="bm-rows">
              <div className="bm-row"><span>Booking ID</span><strong className="bm-id">{booking?.id?.slice(0, 8)}...</strong></div>
              <div className="bm-row"><span>Hotel</span><strong>{hotel.name}</strong></div>
              <div className="bm-row"><span>Room</span><strong>{room.name}</strong></div>
              <div className="bm-row bm-total"><span>Total</span><strong>{formatPrice(total)}</strong></div>
            </div>

            {errorMsg && <p className="bm-error">{errorMsg}</p>}

            <div className="bm-actions">
              <button className="bm-btn secondary" onClick={handleCancel} disabled={loading}>Cancel Booking</button>
              <button className="bm-btn primary" onClick={handleConfirm} disabled={loading}>
                {loading ? 'Confirming...' : '✓ Confirm & Pay'}
              </button>
            </div>
          </>
        )}

        {/* ─── STEP: CONFIRMED ─── */}
        {step === 'confirmed' && (
          <div className="bm-success">
            <div className="bm-success-icon">✓</div>
            <h2>Booking Confirmed!</h2>
            <p>Your room at <strong>{hotel.name}</strong> is confirmed.</p>
            <p className="bm-booking-id">ID: {booking?.id}</p>
            <button className="bm-btn primary" onClick={onClose}>Done</button>
          </div>
        )}

        {/* ─── STEP: ERROR ─── */}
        {step === 'error' && (
          <div className="bm-error-state">
            <div className="bm-error-icon">⚠</div>
            <h2>Oops!</h2>
            <p>{errorMsg}</p>
            <div className="bm-actions">
              <button className="bm-btn secondary" onClick={onClose}>Close</button>
              <button className="bm-btn primary" onClick={() => setStep('review')}>Try Again</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default BookingModal;
