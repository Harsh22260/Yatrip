import { useState, useCallback, useEffect, useRef } from 'react';
import { fetchRouteOptions, geocodeAddress } from '../../services/transportService';
import './RoutePlanner.css';

const MODES = [
  { id: 'car', label: 'Car / Auto', icon: '🚗' },
  { id: 'bike', label: 'Bike', icon: '🛵' },
  { id: 'walk', label: 'Walk', icon: '🚶' },
];

const emptyStop = () => ({
  id: `${Date.now()}-${Math.random()}`,
  text: '',
  coords: null,
  // 'searching' | 'exact' | ... | 'none' (searched, nothing mapped) |
  // 'error' (the lookup itself failed) | null (not looked up yet)
  precision: null,
  lookupError: null,
  houseMatch: null,
  pinned: false,
});

/**
 * True when the text looks like it carries a building or house number.
 *
 * "C-325, Alpha 1" is a door, not a district. When such a query resolves to a
 * whole neighbourhood instead, saying "Area level" is technically true and
 * practically useless: the traveller asked for a doorstep and got a pin that
 * may be a kilometre away. Flagging it lets the UI say what actually happened
 * and offer the map.
 */
const looksLikeHouseNumber = (text) => /\d{1,4}\s*[-/]?\s*[a-z]?\b/i.test(String(text || ''));

/** Rough cost estimate in INR, so the "cheapest" claim has a number behind it. */
const estimateFare = (mode, km) => {
  if (mode === 'walk') return 0;
  if (mode === 'bike') return Math.round(km * 8); // ~₹8/km
  // Auto/cab: ₹13 base + ₹11.5/km, rounded to the nearest 5.
  return Math.round((13 + km * 11.5) / 5) * 5;
};

const RoutePlanner = ({
  onRouteFound,
  userLocation,
  pinCoords,
  onPinRequest,
  onPinConsumed,
}) => {
  const [stops, setStops] = useState([emptyStop(), emptyStop()]);
  const [mode, setMode] = useState('car');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [suggesting, setSuggesting] = useState(null);

  const updateStop = (index, patch) => {
    setStops((prev) =>
      prev.map((s, i) => (i === index ? { ...s, ...patch } : s)),
    );
  };

  const addStop = () => {
    setStops((prev) => [...prev, emptyStop()]);
  };

  const removeStop = (index) => {
    // A route needs an origin and a destination, so never drop below two.
    if (stops.length <= 2) return;
    setStops((prev) => prev.filter((_, i) => i !== index));
  };

  // Kept in a ref because `resolve` has an empty dependency list on purpose:
  // it must not be rebuilt while a debounce is in flight, but it still needs
  // the live position to bias the search.
  const userLocationRef = useRef(userLocation);
  useEffect(() => {
    userLocationRef.current = userLocation;
  }, [userLocation]);

  // The stop currently being placed by hand on the map.
  const [pinIndex, setPinIndex] = useState(null);

  // The page owns the map, so it is the page that learns about a click. When a
  // coordinate arrives, it is applied to whichever stop is waiting for one and
  // then handed straight back, so the same click cannot fill two stops.
  //
  // This is a props-into-state bridge rather than a derived value: there is no
  // way to express "the map was clicked" as render output. The real alternative
  // is lifting the whole stop list into the page, which buys nothing.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (!pinCoords || pinIndex === null) return;
    const [lat, lon] = pinCoords;
    updateStop(pinIndex, {
      coords: [lat, lon],
      label: `Pinned spot (${lat.toFixed(5)}, ${lon.toFixed(5)})`,
      precision: 'pinned',
      pinned: true,
    });
    setPinIndex(null);
    setError(null);
    onPinConsumed?.();
  }, [pinCoords, pinIndex, onPinConsumed]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const requestPin = (index) => {
    setPinIndex(index);
    onPinRequest?.(index);
  };

  // Takes the text as an argument rather than reading `stops` from the closure:
  // a []-dep callback would always see the first render's stops, where every
  // field is empty, so no address would ever resolve.
  const resolve = useCallback(async (index, text) => {
    const query = String(text ?? '').trim();
    if (!query) return;
    setSuggesting(index);
    // A distinct value, because "not searched yet", "searching", "searched and
    // found nothing" and "the search itself failed" have to be told apart to
    // give an honest message.
    updateStop(index, { precision: 'searching', lookupError: null });
    try {
      const hits = await geocodeAddress(query, {
        // Bias towards the traveller's own area so a repeated street name does
        // not resolve to the same street in another city.
        near: userLocationRef.current,
        countrycodes: 'in',
      });
      if (hits.length) {
        const hit = hits[0];
        updateStop(index, {
          coords: [parseFloat(hit.lat), parseFloat(hit.lon)],
          label: hit.display_name,
          // Nominatim can silently fall back to a city when a house number is
          // unknown. Rendering that as if it were the exact address would send
          // the traveller to the wrong place, so the precision is kept.
          precision: hit.precision,
          lookupError: null,
          // Whether the geocoder actually matched the number the traveller
          // typed, as opposed to quietly dropping it and returning the area.
          houseMatch: hit.house_number || null,
        });
      } else {
        // Genuinely absent from OpenStreetMap. Retyping will not help, so the
        // message says so and offers the map instead.
        updateStop(index, { coords: null, label: null, precision: 'none', lookupError: null });
      }
    } catch (err) {
      // A rejected or failed lookup is not the same as "no such place". Told
      // apart so the traveller is not asked to retype a valid address.
      updateStop(index, {
        coords: null,
        label: null,
        precision: 'error',
        lookupError: err?.message || 'Address lookup failed.',
      });
    } finally {
      setSuggesting((s) => (s === index ? null : s));
    }
  }, []);

  // Resolve as the user types, once they pause. Requiring Enter meant a stop
  // that had been typed but not submitted silently contributed no coordinate,
  // and the planner then reported "set a destination" for a field that looked
  // perfectly filled in.
  const debounceRef = useRef(null);
  const handleTextChange = (index, value) => {
    updateStop(index, { text: value, coords: null, label: null, precision: null });
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => resolve(index, value), 700);
  };

  // Abort a pending debounce when a stop is removed, so it cannot write to the
  // wrong index afterwards.
  useEffect(() => () => clearTimeout(debounceRef.current), []);

  const buildPoints = useCallback(() => {
    const points = [];
    if (userLocation && stops[0].useMyLocation) {
      points.push([userLocation[0], userLocation[1]]);
    } else if (stops[0].coords) {
      points.push(stops[0].coords);
    }
    stops.slice(1).forEach((s) => {
      if (s.coords) points.push(s.coords);
    });
    return points;
  }, [stops, userLocation]);

  const plan = async (forceMode) => {
    const points = buildPoints();
    if (points.length < 2) {
      // Name the offending stops. A bare "set a destination" is useless when
      // every field on screen looks filled in.
      const unresolved = stops
        .map((s, i) => ({ s, i }))
        .filter(({ s, i }) => {
          if (i === 0 && s.useMyLocation) return false;
          return !s.coords;
        });

      if (unresolved.length) {
        // The old single message said "still finding" for every case, so a
        // place that OpenStreetMap has simply never heard of looked like it
        // was mid-request forever. "C market" is not a mapped place, and no
        // amount of waiting will produce a result.
        const searching = unresolved.filter(
          ({ s }) => s.precision === null || s.precision === 'searching',
        );
        const unknown = unresolved.filter(({ s }) => s.precision === 'none');
        const failed = unresolved.filter(({ s }) => s.precision === 'error');
        const label = ({ i }) => (i === 0 ? 'the start' : `stop ${String.fromCharCode(65 + i)}`);

        if (failed.length) {
          setError(
            `Could not search ${failed.map(label).join(' and ')}: ` +
              `${failed[0].s.lookupError || 'the address service did not respond.'} ` +
              `Check the spelling, or drop a pin on the map.`,
          );
        } else if (unknown.length) {
          const names = unknown.map(label).join(' and ');
          setError(
            `${names} could not be found on the map. Local markets, colonies and ` +
              `landmarks are often missing from OpenStreetMap — try a nearby road ` +
              `or building, or drop a pin on the map.`,
          );
        } else {
          setError(
            `Still looking up ${searching.map(label).join(' and ')}. Give it a second, ` +
              `or press Enter to search now.`,
          );
        }
        return;
      }
      setError('Set a start and at least one destination.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRouteOptions(points);
      setResult(data);
      const chosen = forceMode || mode;
      const picked = data.options.find((o) => o.profile === chosen) || data.options[0];
      setMode(picked.profile);
      onRouteFound?.(picked);
    } catch (e) {
      setError(e.message || 'Could not plan that route.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rp-card">
      <h3 className="rp-title">🧭 Plan a route</h3>

      {/* Stops, in visiting order */}
      <div className="rp-stops">
        {stops.map((stop, index) => (
          <div
            key={stop.id}
            className={`rp-stop ${stop.coords || (index === 0 && stop.useMyLocation) ? 'is-ok' : stop.text ? 'is-pending' : ''}`}
          >
            <span className={`rp-stop__pin ${index === 0 ? 'is-start' : ''}`}>
              {index === 0 ? 'A' : String.fromCharCode(65 + Math.min(index, 25))}
            </span>

            <div className="rp-stop__field">
              <input
                className="rp-input"
                type="text"
                placeholder={index === 0 ? 'From — address or place' : `Stop ${index} — where next?`}
                value={stop.text}
                disabled={index === 0 && stop.useMyLocation}
                onChange={(e) => handleTextChange(index, e.target.value)}
                onBlur={(e) => {
                  clearTimeout(debounceRef.current);
                  if (e.target.value.trim()) resolve(index, e.target.value);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    clearTimeout(debounceRef.current);
                    resolve(index, e.target.value);
                  }
                }}
              />

              {index === 0 && userLocation && (
                <button
                  type="button"
                  className={`rp-myloc ${stop.useMyLocation ? 'is-on' : ''}`}
                  onClick={() => {
                    const next = !stop.useMyLocation;
                    clearTimeout(debounceRef.current);
                    updateStop(index, {
                      useMyLocation: next,
                      text: next ? 'My current location' : '',
                      coords: null,
                      label: null,
                      precision: null,
                    });
                  }}
                >
                  🎯 My location
                </button>
              )}
            </div>

            {suggesting === index ? (
              <span className="rp-spin" title="Looking up address">⌛</span>
            ) : stop.coords ? (
              <span
                className="rp-ok"
                title={
                  stop.pinned
                    ? 'Position you picked on the map'
                    : stop.precision === 'exact'
                      ? 'Matched to this building'
                      : `Matched to ${stop.precision || 'area'} level`
                }
              >
                {stop.pinned ? '📌' : '✓'}
              </span>
            ) : stop.precision === 'none' ? (
              <span className="rp-miss" title="OpenStreetMap has no match for this name">
                ✕
              </span>
            ) : stop.precision === 'error' ? (
              <span className="rp-warn" title={stop.lookupError || 'Lookup failed'}>
                !
              </span>
            ) : stop.text ? (
              <span className="rp-warn" title="Not resolved yet">?</span>
            ) : null}

            {/* The escape hatch for places OpenStreetMap has never mapped, which
                in India is most local markets, gaddis and unnamed colonies. */}
            <button
              type="button"
              className={`rp-pin ${pinIndex === index ? 'active' : ''}`}
              onClick={() => requestPin(pinIndex === index ? null : index)}
              title="Pick this stop on the map instead of searching for it"
            >
              📌 Pin
            </button>

            <button
              type="button"
              className="rp-remove"
              onClick={() => removeStop(index)}
              disabled={stops.length <= 2}
              title={stops.length <= 2 ? 'A route needs two stops' : 'Remove stop'}
            >
              ✕
            </button>

            {/* Show what the geocoder actually matched, so a city-level
                fallback is visible rather than silently used. */}
            {stop.label && (
              <p className="rp-resolved">
                <span className={`rp-resolved__precision is-${stop.precision || 'area'}`}>
                  {stop.precision === 'exact'
                    ? 'Exact building'
                    : stop.precision === 'house'
                      ? 'House number'
                      : stop.precision === 'street'
                        ? 'Street level'
                        : 'Area level'}
                </span>
                {' — '}
                {stop.label}
              </p>
            )}

            {/* Inline, so the reason is visible while typing rather than only
                after pressing "Show route". */}
            {stop.text && stop.precision === 'none' && (
              <p className="rp-inline-note is-miss">
                Not on the map. Local markets and colonies are often unmapped — use
                📌 Pin and tap the spot, or try a nearby road.
              </p>
            )}
            {stop.precision === 'error' && (
              <p className="rp-inline-note is-error">{stop.lookupError}</p>
            )}

            {/* The important one: a house number the geocoder could not honour.
                Routing to a neighbourhood centroid because that is all the data
                has would send the traveller to the wrong place without saying
                so. */}
            {stop.coords &&
              !stop.pinned &&
              looksLikeHouseNumber(stop.text) &&
              !stop.houseMatch && (
                <p className="rp-inline-note is-warn">
                  OpenStreetMap has no building record for{' '}
                  <strong>{stop.text.split(',')[0].trim()}</strong>, so this pin
                  marks the surrounding area, not that doorstep. Use 📌 Pin to
                  set the exact spot.
                </p>
              )}
          </div>
        ))}

        <button type="button" className="rp-add" onClick={addStop}>
          + Add another stop
        </button>
      </div>

      {/* Travel mode */}
      <div className="rp-modes" role="radiogroup" aria-label="Travel mode">
        {MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            role="radio"
            aria-checked={mode === m.id}
            className={`rp-mode ${mode === m.id ? 'is-active' : ''}`}
            onClick={() => {
              setMode(m.id);
              if (result) plan(m.id);
            }}
          >
            <span aria-hidden="true">{m.icon}</span> {m.label}
          </button>
        ))}
      </div>

      <button type="button" className="rp-go" onClick={() => plan()} disabled={loading}>
        {loading ? 'Planning…' : 'Show route'}
      </button>

      {error && <p className="rp-error">{error}</p>}

      {/* Banner shown while the traveller is choosing a spot on the map. */}
      {pinIndex !== null && (
        <p className="rp-pin-banner">
          📌 Click anywhere on the map to set{' '}
          <strong>{pinIndex === 0 ? 'the start' : `stop ${String.fromCharCode(65 + pinIndex)}`}</strong>,
          or press the Pin button again to cancel.
        </p>
      )}

      {/* Smart comparison across every mode */}
      {result && !error && (
        <div className="rp-result">
          <h4 className="rp-result__title">
            {result.options.length > 1 ? 'Compare options' : 'Route'}
          </h4>
          <ul className="rp-options">
            {result.options.map((o) => {
              const fare = estimateFare(o.profile, o.distance_km);
              const tags = [];
              if (o.profile === result.fastest) tags.push('fastest');
              if (o.profile === result.shortest) tags.push('shortest');
              if (o.profile === result.recommended) tags.push('recommended');
              return (
                <li
                  key={o.profile}
                  className={`rp-option ${o.profile === mode ? 'is-active' : ''}`}
                  onClick={() => {
                    setMode(o.profile);
                    onRouteFound?.(o);
                  }}
                >
                  <span className="rp-option__icon">
                    {MODES.find((m) => m.id === o.profile)?.icon}
                  </span>
                  <span className="rp-option__body">
                    <strong>{MODES.find((m) => m.id === o.profile)?.label}</strong>
                    <em>
                      {o.distance_km} km · {o.duration_min} min
                      {fare > 0 ? ` · ~₹${fare}` : ' · free'}
                    </em>
                    {tags.length > 0 && (
                      <span className="rp-tags">
                        {tags.map((t) => (
                          <span key={t} className={`rp-tag rp-tag--${t}`}>
                            {t}
                          </span>
                        ))}
                      </span>
                    )}
                  </span>
                </li>
              );
            })}
          </ul>

          {/* Turn-by-turn, from the selected mode */}
          {result.options
            .find((o) => o.profile === mode)
            ?.legs?.flatMap((leg) => leg.steps || [])
            .slice(0, 8)
            .map((step, i) => (
              <ol key={i} className="rp-steps">
                <li>{step.instruction}</li>
              </ol>
            ))}
        </div>
      )}
    </div>
  );
};

export default RoutePlanner;
