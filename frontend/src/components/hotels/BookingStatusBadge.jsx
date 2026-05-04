import React from 'react';
import { getStatusInfo } from '../../utils/hotelHelpers';

const BookingStatusBadge = ({ status }) => {
  const { bg, text, label } = getStatusInfo(status);
  return (
    <span style={{
      background: bg,
      color: text,
      padding: '3px 10px',
      borderRadius: '20px',
      fontSize: '0.75rem',
      fontWeight: 600,
      fontFamily: 'DM Sans, sans-serif',
      letterSpacing: '0.03em',
      display: 'inline-block',
    }}>
      {label}
    </span>
  );
};

export default BookingStatusBadge;
