import React from 'react';
import { getNodeTypeMeta } from '../../utils/transportHelpers';
import './NodeCard.css';

const NodeCard = ({ node, onSelect, isSelected, userLocation }) => {
  const { icon, label, color } = getNodeTypeMeta(node.node_type);

  return (
    <div
      className={`nc-card ${isSelected ? 'selected' : ''}`}
      onClick={() => onSelect?.(node)}
      style={{ '--node-color': color }}
    >
      <div className="nc-icon-wrap" style={{ background: `${color}18`, color }}>
        <span>{icon}</span>
      </div>
      <div className="nc-body">
        <div className="nc-header">
          <h4 className="nc-name">{node.name}</h4>
          <span className="nc-type-badge" style={{ background: `${color}18`, color }}>
            {label}
          </span>
        </div>
        <p className="nc-city">🏙️ {node.city}</p>
        {node.address && <p className="nc-address">📍 {node.address}</p>}
      </div>
      {isSelected && <div className="nc-selected-dot" style={{ background: color }} />}
    </div>
  );
};

export default NodeCard;
