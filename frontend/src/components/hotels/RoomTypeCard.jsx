import React, { useState } from 'react';
import { formatPrice, calcNights } from '../../utils/hotelHelpers';
import { useRatePlans } from '../../hooks/useHotels';
import './RoomTypeCard.css';

const RoomTypeCard = ({ room, checkIn, checkOut, onBook }) => {
  const nights = calcNights(checkIn, checkOut);
  const { ratePlans } = useRatePlans(room.id);
  const [selectedPlan, setSelectedPlan] = useState(null);

  const activePlan = ratePlans.find((p) => p.id === selectedPlan) || null;
  const multiplier = activePlan?.price_multiplier || 1;
  const total = parseFloat(room.base_price) * multiplier * (nights || 1);

  return (
    <div className="rtc-card">
      <div className="rtc-top">
        <div>
          <h4 className="rtc-name">{room.name}</h4>
          {room.description && <p className="rtc-desc">{room.description}</p>}
          <div className="rtc-meta">
            <span>👤 {room.capacity} {room.capacity > 1 ? 'guests' : 'guest'}</span>
            <span>🛏 {room.total_units} units</span>
          </div>
        </div>

        <div className="rtc-pricing">
          <span className="rtc-base">{formatPrice(room.base_price)}</span>
          <span className="rtc-label">base / night</span>
          {nights > 0 && (
            <span className="rtc-total">{formatPrice(total)} total</span>
          )}
        </div>
      </div>

      {/* Unit badges */}
      {room.units?.length > 0 && (
        <div className="rtc-units">
          {room.units.slice(0, 6).map((u) => (
            <span key={u.id} className={`rtc-unit ${u.is_available ? 'available' : 'taken'}`}>
              {u.unit_code}
            </span>
          ))}
          {room.units.length > 6 && (
            <span className="rtc-unit-more">+{room.units.length - 6} more</span>
          )}
        </div>
      )}

      {/* Rate plans */}
      {ratePlans.length > 0 && (
        <div className="rtc-plans">
          <p className="rtc-plans-label">Rate Plans</p>
          <div className="rtc-plans-list">
            <button
              className={`rtc-plan-btn ${!selectedPlan ? 'active' : ''}`}
              onClick={() => setSelectedPlan(null)}
            >
              Standard
            </button>
            {ratePlans.map((plan) => (
              <button
                key={plan.id}
                className={`rtc-plan-btn ${selectedPlan === plan.id ? 'active' : ''}`}
                onClick={() => setSelectedPlan(plan.id)}
                title={plan.refundable ? 'Refundable' : 'Non-refundable'}
              >
                {plan.name}
                {plan.refundable ? ' ✓' : ' ✗'}
              </button>
            ))}
          </div>
        </div>
      )}

      <button
        className="rtc-book-btn"
        onClick={() => onBook?.({ room, ratePlan: activePlan })}
        disabled={!checkIn || !checkOut}
      >
        {checkIn && checkOut ? `Book for ${nights} Night${nights > 1 ? 's' : ''}` : 'Select Dates First'}
      </button>
    </div>
  );
};

export default RoomTypeCard;
