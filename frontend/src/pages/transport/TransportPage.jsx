import React, { useState } from 'react';
import { useTransportNodes, useNearbyNodes } from '../../hooks/useTransport';
import TransportMap from '../../components/transport/TransportMap';
import NodeCard from '../../components/transport/NodeCard';
import RoutePlanner from '../../components/transport/RoutePlanner';
import { filterNodes, ALL_NODE_TYPES, getNodeTypeMeta } from '../../utils/transportHelpers';
import './TransportPage.css';

const TransportPage = () => {
  const { nodes, loading, error, refetch } = useTransportNodes();
  const { nodes: nearbyNodes, loading: nearbyLoading, userLocation, locationDenied, getUserLocation } = useNearbyNodes();

  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [selectedNode, setSelectedNode] = useState(null);
  const [routeGeometry, setRouteGeometry] = useState(null);
  const [activeTab, setActiveTab] = useState('map'); // map | list | nearby

  const displayNodes = activeTab === 'nearby' ? nearbyNodes : nodes;
  const filtered = filterNodes(displayNodes, { search, type: typeFilter });

  const handleRouteFound = (route) => {
    setRouteGeometry(route?.geometry || null);
  };

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
                nodes={nodes}
                userLocation={userLocation}
                routeGeometry={routeGeometry}
                selectedNode={selectedNode}
                onNodeClick={setSelectedNode}
                height="520px"
              />
            </div>

            {/* Right: Route Planner + Selected Node */}
            <div className="tp-map-sidebar">
              <RoutePlanner onRouteFound={handleRouteFound} />

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

              {/* Legend */}
              <div className="tp-legend">
                <h4 className="tp-legend-title">Legend</h4>
                <div className="tp-legend-items">
                  {ALL_NODE_TYPES.filter((t) => t !== 'all').map((type) => {
                    const { icon, label, color } = getNodeTypeMeta(type);
                    return (
                      <div key={type} className="tp-legend-item">
                        <span
                          className="tp-legend-dot"
                          style={{ background: color }}
                        >{icon}</span>
                        <span>{label}</span>
                      </div>
                    );
                  })}
                  <div className="tp-legend-item">
                    <span className="tp-legend-user">●</span>
                    <span>Your Location</span>
                  </div>
                </div>
              </div>
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
                      userLocation={userLocation}
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
