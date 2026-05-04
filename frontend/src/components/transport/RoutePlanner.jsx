import React, { useState, useEffect, useRef } from 'react';
import { useRoute, useGeocode } from '../../hooks/useTransport';
import './RoutePlanner.css';

const LocationInput = ({ label, icon, value, onChange, onSelect, placeholder }) => {
  const { results, loading, search, clearResults } = useGeocode();
  const [inputVal, setInputVal] = useState(value?.label || '');
  const [showDropdown, setShowDropdown] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    if (value?.label) setInputVal(value.label);
  }, [value]);

  const handleChange = (e) => {
    const val = e.target.value;
    setInputVal(val);
    setShowDropdown(true);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => search(val), 400);
  };

  const handleSelect = (result) => {
    setInputVal(result.display_name.split(',').slice(0, 2).join(', '));
    onSelect({ lat: parseFloat(result.lat), lon: parseFloat(result.lon), label: result.display_name });
    setShowDropdown(false);
    clearResults();
  };

  return (
    <div className="rp-input-wrap">
      <label className="rp-label">{icon} {label}</label>
      <div className="rp-input-box">
        <input
          className="rp-input"
          type="text"
          value={inputVal}
          onChange={handleChange}
          placeholder={placeholder}
          onFocus={() => setShowDropdown(true)}
          onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
        />
        {inputVal && (
          <button className="rp-clear" onClick={() => { setInputVal(''); onChange(null); }}>✕</button>
        )}
      </div>
      {showDropdown && results.length > 0 && (
        <div className="rp-dropdown">
          {results.map((r, i) => (
            <button key={i} className="rp-dropdown-item" onMouseDown={() => handleSelect(r)}>
              <span className="rp-dropdown-icon">📍</span>
              <span className="rp-dropdown-text">{r.display_name}</span>
            </button>
          ))}
        </div>
      )}
      {loading && <div className="rp-searching">Searching...</div>}
    </div>
  );
};

const RoutePlanner = ({ onRouteFound }) => {
  const [start, setStart] = useState(null);
  const [end, setEnd] = useState(null);
  const { route, loading, error, getRoute, clearRoute } = useRoute();

  const handleGetRoute = async () => {
    if (!start || !end) return;
    await getRoute(start.lat, start.lon, end.lat, end.lon);
  };

  useEffect(() => {
    if (route) onRouteFound?.(route);
  }, [route]);

  const handleClear = () => {
    setStart(null);
    setEnd(null);
    clearRoute();
    onRouteFound?.(null);
  };

  return (
    <div className="rp-card">
      <h3 className="rp-title">🗺️ Route Planner</h3>

      <LocationInput
        label="From"
        icon="🟢"
        value={start}
        onChange={setStart}
        onSelect={setStart}
        placeholder="Search start location..."
      />

      <div className="rp-swap-wrap">
        <div className="rp-line" />
        <button
          className="rp-swap-btn"
          onClick={() => { const tmp = start; setStart(end); setEnd(tmp); }}
          title="Swap"
        >⇅</button>
        <div className="rp-line" />
      </div>

      <LocationInput
        label="To"
        icon="🔴"
        value={end}
        onChange={setEnd}
        onSelect={setEnd}
        placeholder="Search destination..."
      />

      <div className="rp-actions">
        <button
          className="rp-go-btn"
          onClick={handleGetRoute}
          disabled={!start || !end || loading}
        >
          {loading ? '⏳ Finding route...' : '🚀 Get Route'}
        </button>
        {(start || end || route) && (
          <button className="rp-clear-btn" onClick={handleClear}>Clear</button>
        )}
      </div>

      {error && <p className="rp-error">⚠ {error}</p>}

      {route && (
        <div className="rp-result">
          <div className="rp-result-item">
            <span className="rp-result-icon">📏</span>
            <div>
              <span className="rp-result-label">Distance</span>
              <span className="rp-result-val">{route.distance_km} km</span>
            </div>
          </div>
          <div className="rp-result-item">
            <span className="rp-result-icon">⏱️</span>
            <div>
              <span className="rp-result-label">Duration</span>
              <span className="rp-result-val">{route.duration_min} min</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RoutePlanner;
