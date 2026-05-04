import React, { useEffect, useRef, useCallback } from 'react';
import { getNodeTypeMeta, parseLocation } from '../../utils/transportHelpers';
import './TransportMap.css';

// Dynamically load Leaflet (no npm needed - uses CDN)
let leafletLoaded = false;
const loadLeaflet = () => {
  return new Promise((resolve) => {
    if (window.L) { resolve(window.L); return; }
    if (leafletLoaded) {
      const check = setInterval(() => {
        if (window.L) { clearInterval(check); resolve(window.L); }
      }, 50);
      return;
    }
    leafletLoaded = true;

    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
    document.head.appendChild(link);

    const script = document.createElement('script');
    script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
    script.onload = () => resolve(window.L);
    document.head.appendChild(script);
  });
};

const createCustomIcon = (L, color, icon) => {
  return L.divIcon({
    className: '',
    html: `
      <div style="
        background: ${color};
        width: 36px; height: 36px;
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        border: 3px solid #fff;
        box-shadow: 0 3px 12px rgba(0,0,0,0.3);
        display: flex; align-items: center; justify-content: center;
      ">
        <span style="transform: rotate(45deg); font-size: 16px; line-height: 1;">${icon}</span>
      </div>
    `,
    iconSize: [36, 36],
    iconAnchor: [18, 36],
    popupAnchor: [0, -38],
  });
};

const createUserIcon = (L) => {
  return L.divIcon({
    className: '',
    html: `
      <div style="position:relative;">
        <div style="
          background: #3b82f6;
          width: 18px; height: 18px;
          border-radius: 50%;
          border: 3px solid #fff;
          box-shadow: 0 0 0 4px rgba(59,130,246,0.3);
        "></div>
      </div>
    `,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });
};

const TransportMap = ({
  nodes = [],
  userLocation = null,
  routeGeometry = null,
  selectedNode = null,
  onNodeClick,
  onMapClick,
  height = '500px',
}) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef([]);
  const routeLayerRef = useRef(null);
  const userMarkerRef = useRef(null);

  // Initialize map
  useEffect(() => {
    loadLeaflet().then((L) => {
      if (mapInstanceRef.current) return;

      const center = userLocation || [20.5937, 78.9629]; // India center
      const map = L.map(mapRef.current, {
        center,
        zoom: userLocation ? 14 : 5,
        zoomControl: false,
      });

      // Custom zoom position
      L.control.zoom({ position: 'bottomright' }).addTo(map);

      // OSM Tile Layer
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/">OpenStreetMap</a>',
        maxZoom: 19,
      }).addTo(map);

      // Optional: Carto light tiles (cleaner look)
      // L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png').addTo(map);

      if (onMapClick) {
        map.on('click', (e) => onMapClick(e.latlng.lat, e.latlng.lng));
      }

      mapInstanceRef.current = map;
    });

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update node markers
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !window.L) return;
    const L = window.L;

    // Clear old markers
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    nodes.forEach((node) => {
      const coords = parseLocation(node.location);
      if (!coords) return;

      const { icon, color, label } = getNodeTypeMeta(node.node_type);
      const marker = L.marker(coords, {
        icon: createCustomIcon(L, color, icon),
      });

      marker.bindPopup(`
        <div style="font-family: DM Sans, sans-serif; min-width: 160px;">
          <div style="font-size:0.72rem; font-weight:700; color:${color}; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:4px;">
            ${icon} ${label}
          </div>
          <div style="font-weight:700; font-size:0.95rem; color:#1a1209; margin-bottom:4px;">${node.name}</div>
          ${node.address ? `<div style="font-size:0.78rem; color:#78716c;">📍 ${node.address}</div>` : ''}
          <div style="font-size:0.78rem; color:#78716c; margin-top:2px;">🏙️ ${node.city}</div>
          ${onNodeClick ? `<button onclick="window._transportNodeClick(${node.id})" style="margin-top:8px; background:${color}; color:#fff; border:none; padding:5px 12px; border-radius:6px; font-size:0.78rem; cursor:pointer; width:100%;">Set as Destination</button>` : ''}
        </div>
      `, { maxWidth: 220 });

      marker.addTo(map);
      markersRef.current.push(marker);
    });

    // Global click handler for popup buttons
    window._transportNodeClick = (id) => {
      const node = nodes.find((n) => n.id === id);
      if (node && onNodeClick) onNodeClick(node);
    };
  }, [nodes, onNodeClick]);

  // Update user location marker
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !window.L || !userLocation) return;
    const L = window.L;

    if (userMarkerRef.current) userMarkerRef.current.remove();

    userMarkerRef.current = L.marker(userLocation, {
      icon: createUserIcon(L),
      zIndexOffset: 1000,
    })
      .bindPopup('<div style="font-family: DM Sans, sans-serif; font-weight:600;">📍 You are here</div>')
      .addTo(map);

    map.setView(userLocation, 14, { animate: true });
  }, [userLocation]);

  // Draw route
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !window.L) return;
    const L = window.L;

    if (routeLayerRef.current) routeLayerRef.current.remove();

    if (routeGeometry) {
      routeLayerRef.current = L.geoJSON(routeGeometry, {
        style: {
          color: '#6366f1',
          weight: 5,
          opacity: 0.85,
          dashArray: null,
          lineCap: 'round',
          lineJoin: 'round',
        },
      }).addTo(map);

      map.fitBounds(routeLayerRef.current.getBounds(), { padding: [40, 40] });
    }
  }, [routeGeometry]);

  return (
    <div className="tm-wrapper" style={{ height }}>
      <div ref={mapRef} className="tm-map" />
      <div className="tm-attribution">
        Map data © <a href="https://openstreetmap.org" target="_blank" rel="noreferrer">OpenStreetMap</a>
      </div>
    </div>
  );
};

export default TransportMap;
