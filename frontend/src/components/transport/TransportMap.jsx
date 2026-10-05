import { useState, useEffect, useRef, useCallback } from 'react';
import { getNodeTypeMeta, parseLocation } from '../../utils/transportHelpers';
import './TransportMap.css';

// Dynamically load Leaflet (no npm needed - uses CDN)
let leafletLoaded = false;
let leafletFailed = false;
const loadLeaflet = () => {
  return new Promise((resolve, reject) => {
    if (window.L) { resolve(window.L); return; }
    if (leafletFailed) { reject(new Error('Leaflet previously failed to load')); return; }
    if (leafletLoaded) {
      const check = setInterval(() => {
        if (window.L) { clearInterval(check); resolve(window.L); }
      }, 50);
      return;
    }
    leafletLoaded = true;

    // Without a timeout a blocked CDN leaves this promise pending forever, and
    // the map stays blank with no explanation.
    const timer = setTimeout(() => {
      leafletLoaded = false;
      leafletFailed = true;
      reject(new Error('Timed out loading the map library (unpkg.com unreachable)'));
    }, 12000);

    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
    document.head.appendChild(link);

    const script = document.createElement('script');
    script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
    script.onload = () => { clearTimeout(timer); resolve(window.L); };
    script.onerror = () => {
      clearTimeout(timer);
      leafletLoaded = false;
      leafletFailed = true;
      reject(new Error('Could not load the map library. Check your internet connection.'));
    };
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

/** Compass arrow that points along travel direction, not north. */
const createArrowIcon = (L, bearing = 0) => {
  return L.divIcon({
    className: '',
    html: `
      <div style="
        transform: rotate(${bearing}deg);
        transition: transform 0.4s ease;
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.45));
      ">
        <svg width="34" height="34" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="11" fill="#2563eb" stroke="#fff" stroke-width="1.6"/>
          <path d="M12 4.5 L17 18 L12 15 L7 18 Z" fill="#fff"/>
        </svg>
      </div>
    `,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
  });
};

/** Initial bearing from one point to another, in degrees clockwise from north. */
const bearingBetween = ([lat1, lon1], [lat2, lon2]) => {
  const toRad = (d) => (d * Math.PI) / 180;
  const dLon = toRad(lon2 - lon1);
  const y = Math.sin(dLon) * Math.cos(toRad(lat2));
  const x =
    Math.cos(toRad(lat1)) * Math.sin(toRad(lat2)) -
    Math.sin(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.cos(dLon);
  return (((Math.atan2(y, x) * 180) / Math.PI) + 360) % 360;
};

const TransportMap = ({
  nodes = [],
  userLocation = null,
  routeGeometry = null,
  selectedNode = null,
  onNodeClick,
  onMapClick,
  onRequestLocation,
  onStartNavigation,
  height = '500px',
}) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef([]);
  const routeLayerRef = useRef(null);
  const userMarkerRef = useRef(null);
  const circleRef = useRef(null);
  const trackLayerRef = useRef(null);
  const arrowMarkerRef = useRef(null);
  // Effects below need the map instance, but the map initialises
  // asynchronously once Leaflet arrives. `mapReady` is the signal that makes
  // those effects re-run: without it a location that resolved before Leaflet
  // loaded was dropped permanently, because `userLocation` never changed again
  // and the effect had already bailed out.
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState(null);
  const [locating, setLocating] = useState(false);
  const [navActive, setNavActive] = useState(false);
  const [bearing, setBearing] = useState(null);

  const focusUser = useCallback(() => {
    const map = mapInstanceRef.current;
    if (!map || !userLocation) return;
    setLocating(true);
    map.setView(userLocation, 15, { animate: true });
    if (circleRef.current) circleRef.current.remove();
    const radius = (userLocation[2] || 60) * 2;
    circleRef.current = window.L
      .circle(userLocation, { radius, color: '#3b82f6', weight: 1, fillOpacity: 0.12 })
      .addTo(map);
    setTimeout(() => setLocating(false), 900);
  }, [userLocation]);

  // Location is requested only when the user presses the target button below.
  // Firing it on mount threw a permission dialog over the map as the page
  // loaded, which broke the map for the whole session -- and the request was
  // duplicated, so the browser saw two competing prompts.

  // Initialize map
  useEffect(() => {
    let cancelled = false;

    loadLeaflet()
      .then((L) => {
        if (cancelled || mapInstanceRef.current || !mapRef.current) return;

        const center = userLocation || [20.5937, 78.9629]; // India centre
        const map = L.map(mapRef.current, {
          center,
          zoom: userLocation ? 13 : 5,
          zoomControl: false,
        });

        L.control.zoom({ position: 'bottomright' }).addTo(map);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '© <a href="https://www.openstreetmap.org/">OpenStreetMap</a>',
          maxZoom: 19,
        }).addTo(map);

        if (onMapClick) {
          map.on('click', (e) => onMapClick(e.latlng.lat, e.latlng.lng));
        }

        mapInstanceRef.current = map;
        setMapReady(true);
        setMapError(null);
      })
      .catch((err) => {
        if (!cancelled) setMapError(err.message || 'Map failed to load');
      });

    return () => {
      cancelled = true;
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
      setMapReady(false);
    };
    // Intentionally mount-only: re-running this would tear down the map.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Location is requested only when the user presses the target button below.
  // Firing it on mount threw a permission dialog over the map as the page
  // loaded, which broke the map for the whole session -- and the request was
  // duplicated, so the browser saw two competing prompts.

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
  }, [nodes, onNodeClick, mapReady]);

  // Update user location marker.
  // `mapReady` is in the deps so a fix that arrived before Leaflet finished
  // loading is applied once the map exists.
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

    map.setView(userLocation, 13, { animate: true });
    if (circleRef.current) circleRef.current.remove();
    circleRef.current = L.circle(userLocation, {
      radius: (userLocation[2] || 60) * 2,
      color: '#3b82f6',
      weight: 1,
      fillOpacity: 0.12,
    }).addTo(map);
  }, [userLocation, mapReady]);

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
  }, [routeGeometry, mapReady]);

  // Pan to a node picked from the list, the way a map app centres a search hit.
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !window.L || !selectedNode) return;
    const coords = parseLocation(selectedNode.location);
    if (!coords) return;
    map.setView(coords, Math.max(map.getZoom(), 15), { animate: true });
    markersRef.current
      .slice()
      .reverse()
      .find((m) => m.getLatLng().lat === coords[0] && m.getLatLng().lng === coords[1])
      ?.openPopup();
  }, [selectedNode, mapReady]);

  // ── Navigation: travelled track + direction arrow ──────────────────────
  // watchPosition reports a stream of fixes. Each one is appended to a polyline
  // so the route actually travelled is drawn behind the user, and the arrow is
  // rotated to the bearing between the last two fixes -- pointing the way you
  // are going rather than north.
  useEffect(() => {
    if (!mapReady || !navigator.geolocation || !window.L) return undefined;
    const map = mapInstanceRef.current;
    const L = window.L;
    let cancelled = false;
    let last = null;

    if (trackLayerRef.current) trackLayerRef.current.remove();
    trackLayerRef.current = L.polyline([], {
      color: '#2563eb',
      weight: 5,
      opacity: 0.75,
      lineCap: 'round',
      lineJoin: 'round',
    }).addTo(map);

    if (arrowMarkerRef.current) arrowMarkerRef.current.remove();
    arrowMarkerRef.current = L.marker([0, 0], {
      icon: createArrowIcon(L),
      zIndexOffset: 1100,
      interactive: false,
    });

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        if (cancelled || !mapInstanceRef.current) return;
        const { latitude, longitude, heading } = pos.coords;
        const here = [latitude, longitude];

        trackLayerRef.current?.addLatLng(here);

        let angle = heading;
        if (angle === null || angle === undefined) {
          if (last) angle = bearingBetween(last, here);
        }
        if (angle !== null && angle !== undefined) {
          arrowMarkerRef.current
            ?.setLatLng(here)
            .setIcon(createArrowIcon(L, angle))
            .addTo(map);
          setBearing(angle);
        } else {
          arrowMarkerRef.current?.setLatLng(here).addTo(map);
        }
        last = here;
      },
      () => {
        /* permission denied or unavailable: the route arrow simply stays hidden */
      },
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 },
    );

    return () => {
      cancelled = true;
      navigator.geolocation.clearWatch(watchId);
      if (trackLayerRef.current) { trackLayerRef.current.remove(); trackLayerRef.current = null; }
      if (arrowMarkerRef.current) { arrowMarkerRef.current.remove(); arrowMarkerRef.current = null; }
    };
  }, [mapReady, navActive]);

  return (
    <div className="tm-wrapper" style={{ height }}>
      <div ref={mapRef} className="tm-map" />

      {mapError && (
        <div className="tm-fallback" role="alert">
          <strong>Map could not load</strong>
          <p>{mapError}</p>
          <p className="tm-fallback__hint">
            The map tiles and library load from the internet. Reconnect and press retry.
          </p>
          <button type="button" onClick={() => window.location.reload()}>
            Retry
          </button>
        </div>
      )}

      <div className="tm-controls">
        <button
            type="button"
            className="tm-btn"
            onClick={() => {
              // Request first, then centre once the fix lands. Previously the
              // button was disabled until a location already existed, so the one
              // control that could obtain one was itself unclickable.
              onRequestLocation?.();
              focusUser();
            }}
            title="Show my current location"
          >
          {locating ? '⌛' : '🎯'}
        </button>
        <button
          type="button"
          className={`tm-btn ${navActive ? 'tm-btn--on' : ''}`}
          onClick={() => {
            setNavActive((v) => !v);
            onStartNavigation?.(!navActive);
          }}
          title="Track my journey and show a direction arrow"
          aria-pressed={navActive}
        >
          🧭
        </button>
      </div>

      {navActive && bearing !== null && (
        <div className="tm-nav-hud">
          <span className="tm-nav-hud__arrow" style={{ transform: `rotate(${bearing}deg)` }}>
            ➤
          </span>
          <span>{Math.round(bearing)}°</span>
        </div>
      )}

      <div className="tm-attribution">
        Map data © <a href="https://openstreetmap.org" target="_blank" rel="noreferrer">OpenStreetMap</a>
      </div>
    </div>
  );
};

export default TransportMap;
