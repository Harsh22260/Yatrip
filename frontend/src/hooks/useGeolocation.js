import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Geolocation with real diagnostics.
 *
 * The previous version discarded the error object entirely
 * (`() => setLocationDenied(true)`), so a blocked permission, an insecure
 * origin and a GPS timeout all looked identical: a dead button. Each cause has
 * a different fix, so the message has to name the cause.
 *
 * The single most common failure here is not a bug in this app at all:
 * browsers only expose `navigator.geolocation` in a *secure context*, meaning
 * https:// or exactly localhost. Opened over a LAN IP such as
 * http://192.168.1.5:5173 it is blocked outright, with no prompt shown.
 */

export const LOCATION_ERRORS = {
  1: {
    code: 'denied',
    title: 'Permission denied',
    help:
      'Location access is blocked for this site. Click the padlock or the '
      + 'location icon beside the address bar, allow location, then press Retry.',
  },
  2: {
    code: 'unavailable',
    title: 'Position unavailable',
    help:
      'Your device could not determine a position. Turn on location services '
      + '(and GPS on Android), move near a window, then press Retry.',
  },
  3: {
    code: 'timeout',
    title: 'Timed out',
    help:
      'Taking too long to get a fix. This is common indoors. Try again outdoors, '
      + 'or use the manual city search below.',
  },
};

const insecureContextHint = {
  code: 'insecure',
  title: 'Blocked by the browser (not HTTPS)',
  help:
    'Browsers only allow live location on https:// or exactly http://localhost. '
    + 'Opening the app via a LAN IP (http://192.168.x.x:5173) blocks it with no '
    + 'prompt. Use http://localhost:5173, or put the app behind HTTPS.',
};

/** Is this origin one the browser allows geolocation on? */
export const isGeolocationAllowed = () =>
  typeof window !== 'undefined' &&
  window.isSecureContext === true &&
  typeof navigator !== 'undefined' &&
  !!navigator.geolocation;

export const useGeolocation = ({ onFix } = {}) => {
  const [coords, setCoords] = useState(null);
  const [accuracy, setAccuracy] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [attempts, setAttempts] = useState(0);
  const onFixRef = useRef(onFix);

  // Keep the callback fresh without touching the ref during render.
  useEffect(() => {
    onFixRef.current = onFix;
  }, [onFix]);

  const locate = useCallback(() => {
    setError(null);

    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      setError({ ...insecureContextHint, code: 'unsupported' });
      setLoading(false);
      return;
    }

    // A false here means the page is on http://<LAN-IP>, where the browser
    // removes the API entirely. Check before calling, or the call just never
    // fires its callbacks.
    if (window.isSecureContext === false) {
      setError(insecureContextHint);
      setLoading(false);
      return;
    }

    setLoading(true);
    setAttempts((n) => n + 1);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude, accuracy: acc } = pos.coords;
        setCoords({ lat: latitude, lon: longitude });
        setAccuracy(acc ?? null);
        setLoading(false);
        setError(null);
        onFixRef.current?.({ lat: latitude, lon: longitude, accuracy: acc ?? null });
      },
      (err) => {
        setLoading(false);
        const known = LOCATION_ERRORS[err?.code];
        setError({
          code: known?.code || 'unknown',
          title: known?.title || 'Location failed',
          help: known?.help || `The browser reported: ${err?.message || 'unknown error'}`,
          raw: err?.code ?? null,
        });
      },
      {
        enableHighAccuracy: true,
        timeout: 20000,
        // Never serve a fix older than 30s: a stale one puts the user in the
        // wrong place, which is worse than no marker at all.
        maximumAge: 30000,
      },
    );
  }, []);

  return {
    coords,
    accuracy,
    loading,
    error,
    locate,
    retry: locate,
    attempts,
    supported: typeof navigator !== 'undefined' && !!navigator.geolocation,
    secureContext: typeof window !== 'undefined' ? window.isSecureContext : false,
  };
};

export default useGeolocation;
