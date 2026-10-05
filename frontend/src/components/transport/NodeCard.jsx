import { getNodeTypeMeta } from '../../utils/transportHelpers';
import PlaceImage from '../PlaceImage';
import './NodeCard.css';

const formatDistance = (km) => {
  if (km === null || km === undefined) return null;
  return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`;
};

const NodeCard = ({ node, onSelect, onDirections, isSelected, canRoute }) => {
  const { icon, label, color } = getNodeTypeMeta(node.node_type);
  const distance = formatDistance(node.distance_km);

  return (
    <article
      className={`nc-card ${isSelected ? 'selected' : ''}`}
      style={{ '--node-color': color }}
    >
      <PlaceImage
        src={node.image_url}
        alt={node.name}
        category={node.node_type}
        name={node.name}
        aspect="16 / 9"
        badge={label}
        className="nc-media"
      />

      {/* The body is its own button rather than wrapping the whole card in one:
          a "Directions" button cannot be nested inside another button, and the
          invalid nesting also broke keyboard activation of the outer control. */}
      <button type="button" className="nc-body nc-body--button" onClick={() => onSelect?.(node)}>
        <div className="nc-header">
          <h4 className="nc-name">
            <span aria-hidden="true">{icon}</span> {node.name}
          </h4>
          {node.code && <span className="nc-code">{node.code}</span>}
        </div>

        {node.operator && <p className="nc-operator">{node.operator}</p>}

        <div className="nc-meta">
          {distance && (
            <span className="nc-chip nc-chip--distance" title="Distance from you">
              {distance} away
            </span>
          )}
          {node.city && <span className="nc-chip">📍 {node.city}</span>}
          {(node.route_refs || []).slice(0, 2).map((ref) => (
            <span key={ref} className="nc-chip nc-chip--route">
              {ref}
            </span>
          ))}
        </div>

        {(node.amenities || []).length > 0 && (
          <div className="nc-meta">
            {node.amenities.slice(0, 4).map((a) => (
              <span key={a} className="nc-chip nc-chip--amenity">
                {a.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        )}

        {node.address && <p className="nc-address">🏠 {node.address}</p>}
      </button>

      {/* Every hub in All Nodes and Nearby gets the same treatment: plot a route
          from where the traveller is standing to this exact place. */}
      <div className="nc-actions">
        <button
          type="button"
          className="nc-directions"
          onClick={() => onDirections?.(node)}
          disabled={!onDirections}
          title={
            canRoute
              ? 'Show the route from your current location'
              : 'Turn on your location to get directions'
          }
        >
          <span aria-hidden="true">🧭</span> Directions
        </button>
        {!canRoute && onDirections && (
          <span className="nc-directions-hint">location needed</span>
        )}
      </div>

      {isSelected && <span className="nc-selected-dot" style={{ background: color }} />}
    </article>
  );
};

export default NodeCard;
