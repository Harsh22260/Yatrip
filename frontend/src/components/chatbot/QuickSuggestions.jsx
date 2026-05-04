import React from 'react';
import { QUICK_SUGGESTIONS } from '../../utils/chatHelpers';
import './QuickSuggestions.css';

const QuickSuggestions = ({ onSelect, visible }) => {
  if (!visible) return null;
  return (
    <div className="qs-wrap">
      <p className="qs-label">✨ Quick questions</p>
      <div className="qs-grid">
        {QUICK_SUGGESTIONS.map((s, i) => (
          <button key={i} className="qs-btn" onClick={() => onSelect(s.text)}>
            {s.label}
          </button>
        ))}
      </div>
    </div>
  );
};

export default QuickSuggestions;
