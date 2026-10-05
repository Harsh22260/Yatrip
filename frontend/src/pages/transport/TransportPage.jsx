import { useState, useCallback } from 'react';
import { useTransportNodes, useNearbyNodes } from '../../hooks/useTransport';
import TransportMap from '../../components/transport/TransportMap';
import NodeCard from '../../components/transport/NodeCard';
import RoutePlanner from '../../components/transport/RoutePlanner';
import { fetchMultiRoute } from '../../services/transportService';
import { filterNodes, ALL_NODE_TYPES, getNodeTypeMeta } from '../../utils/transportHelpers';
import './TransportPage.css';

const TransportPage = () => {
  const { nodes, loading, error, refetch } = useTransportNodes();
  const {
    nodes: nearbyNodes,
    byType,
    radiusKm,
    loading: nearbyLoading,
    userLocation,
    locationDenied,
    getUserLocation,
    loadCurrentArea,
    loadingArea,
    areaProgress,
    loadError,
    areaResult,
    geo,
  } = useNearbyNodes();

  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [selectedNode, setSelectedNode] = useState(null);
  const [routeGeometry, setRouteGeometry] = useState(null);
  const [activeTab, setActiveTab] = useState('map'); // map | list | nearby

  const locating = geo?.loading ?? false;
  // Only surface the geolocation failure; an API error is a different problem.
  const locationError = geo?.error
    ? { ...geo.error, secureOk: geo.secureContext }
    : null;

  // Once the traveller's position is known, the map shows what is around them
  // rather than the whole imported catalogue. Without this the legend counted
  // 33 bus stands from Bengaluru while the user stood in Greater Noida.
  // The map is GPS-scoped when a location is known, with no fallback to the whole
  // catalogue: an empty result means "no stops here yet", and silently swapping
  // in Bengaluru's hubs while the user stands in Greater Noida was exactly the
  // bug this replaces. `All Nodes` stays global on purpose, since that is the
  // tab whose whole purpose is browsing everything.
  const legendCounts = userLocation ? byType : null;

  const displayNodes = activeTab === 'nearby' ? nearbyNodes : nodes;
  const mapNodes = userLocation ? nearbyNodes : nodes;
  const filtered = filterNodes(displayNodes, { search, type: typeFilter });

  const handleRouteFound = (route) => {
    setRouteGeometry(route?.geometry || null);
  };

  // "Directions" on any card, in either list: route from where the traveller is
  // standing to that hub, then hand the map the geometry to draw.
  const [directionTarget, setDirectionTarget] = useState(null);
  const [directionLoading, setDirectionLoading] = useState(false);
  const [directionError, setDirectionError] = useState(null);

  const handleDirections = async (node) => {
    if (!userLocation) {
      setDirectionError('Turn on your location first to get directions.');
      getUserLocation();
      return;
    }
    const lat = Number(node.latitude ?? node.lat);
    const lon = Number(node.longitude ?? node.lng ?? node.lon);
    if (Number.isNaN(lat) || Number.isNaN(lon)) {
      setDirectionError('This stop has no coordinates to route to.');
      return;
    }

    setDirectionTarget(node);
    setDirectionLoading(true);
    setDirectionError(null);
    setSelectedNode(node);
    // The route lives on the map, so leave whichever list the traveller was
    // reading rather than stranding the line somewhere off-screen.
    setActiveTab('map');
    try {
      // Through the backend rather than a public OSRM demo call from the
      // browser: it keeps the request on our own origin, lets the server cache
      // the geometry, and uses the same per-profile routers the planner uses.
      const route = await fetchMultiRoute(
        [
          [userLocation[0], userLocation[1]],
          [lat, lon],
        ],
        'car'
      );
      setRouteGeometry(route?.geometry || null);
    } catch (err) {
      setDirectionError(
        err?.message || 'Could not build a route to this stop. Try again shortly.'
      );
    } finally {
      setDirectionLoading(false);
    }
  };

  // ─── Pick-a-stop-on-the-map ───────────────────────────────────
  // OpenStreetMap has never mapped "C market", so a text search alone leaves
  // the traveller stuck. Pinning lets them place any stop by hand, which is how
  // a local bus stop or a market entrance actually gets used.
  //
  // The stop list itself stays inside RoutePlanner; the page only holds the
  // clicked coordinate and hands it back, which avoids lifting all of that
  // state up for the sake of one click.
  const [pinCoords, setPinCoords] = useState(null);

  // The map registers its click handler once, at creation, so this must be
  // stable or the handler ends up bound to a stale closure.
  const handleMapClick = useCallback((lat, lon) => {
    setPinCoords([lat, lon]);
  }, []);

  return (
    <div className="tp-page">
      {/* Header */}
      <header className="tp-header">
        <h1 className="tp-title">Transport Map</h1>
        <p className="tp-sub">Bus stands, Metro, Auto & Taxi near you</p>
      </header>

      {/* Tab Nav */}
      <div className="tp-tabs">
        {['map', 'list', 'nearby'].map((tab) => (
          <button
            key={tab}
            className={`tp-tab ${activeTab === tab ? 'active' : ''}`}
            onClick={() => {
              setActiveTab(tab);
              if (tab === 'nearby' && !userLocation && !locationDenied) getUserLocation();
            }}
          >
            {tab === 'map' ? '🗺️ Map View' : tab === 'list' ? '📋 All Nodes' : '📍 Nearby'}
          </button>
        ))}
      </div>

      <div className="tp-body">
        {/* MAP TAB */}
        {activeTab === 'map' && (
          <div className="tp-map-layout">
            {/* Left: Map */}
            <div className="tp-map-section">
              <TransportMap
                nodes={mapNodes}
                userLocation={userLocation}
                routeGeometry={routeGeometry}
                selectedNode={selectedNode}
                onNodeClick={setSelectedNode}
                onMapClick={handleMapClick}
                onRequestLocation={getUserLocation}
                height="520px"
              />
            </div>

            {/* Right: Route Planner + Legend + Selected Node */}
            <div className="tp-map-sidebar">
              {/* Live location status is always visible, not buried in a tab. */}
              <div className={`tp-geo-status ${userLocation ? 'is-live' : ''}`}>
                {userLocation ? (
                  <>
                    <span className="tp-geo-status__dot" />
                    <span>
                      Live location on
                      {geo?.accuracy ? ` · ±${Math.round(geo.accuracy)} m` : ''}
                    </span>
                  </>
                ) : (
                  <>
                    <span className="tp-geo-status__off">📍</span>
                    <span>Live location off</span>
                    <button
                      type="button"
                      className="tp-geo-status__btn"
                      onClick={getUserLocation}
                      disabled={locating}
                    >
                      {locating ? 'Locating…' : 'Turn on'}
                    </button>
                  </>
                )}
              </div>

              <RoutePlanner
                onRouteFound={handleRouteFound}
                userLocation={userLocation}
                pinCoords={pinCoords}
                onPinConsumed={() => setPinCoords(null)}
              />

              {/* Feedback for the per-card "Directions" action. Rendered here so
                  it is visible from the map tab too, since that action switches
                  the page over to the map. */}
              {(directionLoading || directionError || directionTarget) && (
                <div className="tp-direction-status" role="status">
                  {directionLoading && (
                    <p>🧭 Plotting your route to {directionTarget?.name}…</p>
                  )}
                  {directionError && <p className="tp-direction-status__err">{directionError}</p>}
                  {!directionLoading && !directionError && directionTarget && (
                    <p className="tp-direction-status__ok">
                      Route to {directionTarget?.name} shown on the map
                    </p>
                  )}
                </div>
              )}

              {/* Legend sits in the sidebar, next to the map it explains.
                  Counts are scoped to the traveller's radius once the position
                  is known, so a type showing 0 genuinely means "none around
                  here" rather than "none imported in the country". */}
              <div className="tp-legend">
                <h4 className="tp-legend-title">
                  Legend
                  {legendCounts ? (
                    <span className="tp-legend-scope">within {radiusKm} km of you</span>
                  ) : (
                    <span className="tp-legend-scope">all imported hubs</span>
                  )}
                </h4>
                <div className="tp-legend-items">
                  {ALL_NODE_TYPES.filter((t) => t !== 'all').map((type) => {
                    const { icon, label, color } = getNodeTypeMeta(type);
                    const count = legendCounts
                      ? (legendCounts[type] || 0)
                      : nodes.filter((n) => n.node_type === type).length;
                    return (
                      <div key={type} className="tp-legend-item">
                        <span className="tp-legend-dot" style={{ background: color }}>
                          {icon}
                        </span>
                        <span>{label}</span>
                        <span
                          className={`tp-legend-count ${count === 0 && legendCounts ? 'is-zero' : ''}`}
                        >
                          {count}
                        </span>
                      </div>
                    );
                  })}
                  <div className="tp-legend-item">
                    <span className="tp-legend-user">●</span>
                    <span>Your Location</span>
                    <span className="tp-legend-count">{userLocation ? 'live' : 'off'}</span>
                  </div>
                </div>
              </div>

              {/* On-demand import: the catalogue only helps if the traveller's
                  own area has actually been fetched from OSM. */}
              {userLocation && (
                <div className="tp-load-area">
                  <button
                    type="button"
                    className="tp-load-area__btn"
                    onClick={() => loadCurrentArea(25)}
                    disabled={loadingArea}
                  >
                    {loadingArea ? 'Importing…' : '📥 Load transport around me'}
                  </button>
                  <p className="tp-load-area__hint">
                    Fetches bus, auto, metro, rail and airport hubs within 25 km
                    of your current position from OpenStreetMap. Takes a couple of
                    minutes — you can keep using the app while it runs.
                  </p>
                  {/* Progress is shown live so the wait is legible. Without it the
                      button appears frozen and reads as broken. */}
                  {loadingArea && areaProgress && (
                    <p className="tp-load-area__progress" role="status">
                      {areaProgress}
                    </p>
                  )}
                  {!loadingArea && areaResult && (
                    <p className="tp-load-area__done">
                      Imported {areaResult.created ?? 0} new hub
                      {areaResult.created === 1 ? '' : 's'} · {areaResult.count} now
                      around you
                    </p>
                  )}
                  {loadError && <p className="tp-load-area__err">{loadError}</p>}
                </div>
              )}

              {locationError && (
                <div className="tp-geo-error" role="alert">
                  <strong>📍 Live location unavailable</strong>
                  <p className="tp-geo-error__title">{locationError.title}</p>
                  <p className="tp-geo-error__help">{locationError.help}</p>
                  {!locationError.secureOk && (
                    <p className="tp-geo-error__url">
                      You are on <code>{window.location.origin}</code>
                    </p>
                  )}
                  <button
                    type="button"
                    className="tp-geo-retry"
                    onClick={getUserLocation}
                    disabled={locating}
                  >
                    {locating ? 'Locating…' : 'Retry location'}
                  </button>
                </div>
              )}

              {selectedNode && (
                <div className="tp-selected-node">
                  <h4 className="tp-selected-title">📍 Selected Node</h4>
                  <NodeCard
                    node={selectedNode}
                    isSelected={true}
                    onSelect={() => {}}
                  />
                  <button className="tp-clear-selection" onClick={() => setSelectedNode(null)}>
                    ✕ Clear
                  </button>
                </div>
              )}

            </div>
          </div>
        )}

        {/* LIST & NEARBY TABS */}
        {(activeTab === 'list' || activeTab === 'nearby') && (
          <div className="tp-list-layout">
            {/* Filters */}
            <div className="tp-list-filters">
              <div className="tp-search-wrap">
                <input
                  className="tp-search"
                  type="text"
                  placeholder="Search nodes..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
                <span>🔍</span>
              </div>

              <div className="tp-type-filters">
                {ALL_NODE_TYPES.map((type) => {
                  const meta = type === 'all' ? { icon: '🗺️', label: 'All' } : getNodeTypeMeta(type);
                  return (
                    <button
                      key={type}
                      className={`tp-type-btn ${typeFilter === type ? 'active' : ''}`}
                      onClick={() => setTypeFilter(type)}
                    >
                      {meta.icon} {meta.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Nearby button */}
            {activeTab === 'nearby' && !userLocation && (
              <button className="tp-locate-btn" onClick={getUserLocation} disabled={nearbyLoading}>
                {nearbyLoading ? '⏳ Getting location...' : '📍 Use My Location'}
              </button>
            )}

            {locationDenied && (
              <div className="tp-denied">
                ⚠ Location access denied. Please enable location in your browser.
              </div>
            )}

            {/* Nodes Grid */}
            {(loading || nearbyLoading) && (
              <div className="tp-grid">
                {[1,2,3,4,5,6].map((i) => <div key={i} className="tp-skeleton" />)}
              </div>
            )}

            {error && (
              <div className="tp-error">⚠ {error} <button onClick={refetch}>Retry</button></div>
            )}

            {!loading && !nearbyLoading && filtered.length === 0 && (
              <div className="tp-empty">
                <p>🚌 No transport nodes found.</p>
              </div>
            )}

            {!loading && !nearbyLoading && filtered.length > 0 && (
              <>
                <p className="tp-count">{filtered.length} node{filtered.length !== 1 ? 's' : ''} found</p>
                <div className="tp-grid">
                  {filtered.map((node) => (
                    <NodeCard
                      key={node.id}
                      node={node}
                      isSelected={selectedNode?.id === node.id}
                      onSelect={setSelectedNode}
                      onDirections={handleDirections}
                      canRoute={!!userLocation}
                    />
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default TransportPage;
