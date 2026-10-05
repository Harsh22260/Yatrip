/**
 * Shared API plumbing.
 *
 * Two problems this fixes:
 *
 * 1. Endpoint drift. The hotels app is mounted under `/api/hotels/`, so the
 *    routes are `/api/hotels/hotels/` and `/api/hotels/bookings/`. The service
 *    layer was calling `/api/hotels/` and `/api/bookings/`, which 404 on every
 *    request. Paths are now declared once, here.
 * 2. Error handling. Callers used to do `throw new Error(JSON.stringify(err))`,
 *    so the UI rendered raw JSON. This module always throws an Error with a
 *    readable message and keeps the parsed body on `.data`.
 */

const RAW_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

/** Normalised base, guaranteed to have exactly one trailing slash. */
export const API_BASE = RAW_BASE.replace(/\/+$/, '');

/** Join the base with a path, collapsing duplicate slashes. */
export const apiUrl = (path) => `${API_BASE}/${String(path).replace(/^\/+/, '')}`;

/** Read the CSRF cookie. It carries no authority; it is echoed back as a header. */
export const getCsrfToken = () => {
  try {
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : null;
  } catch {
    return null;
  }
};

export const buildHeaders = ({ json = true, auth = true, method = 'GET' } = {}) => {
  const headers = {};
  if (json) headers['Content-Type'] = 'application/json';

  // The access token is an HttpOnly cookie now, so there is nothing to read
  // here and nothing to attach. The browser sends it via credentials: 'include'.
  // CSRF is the other half of that trade: because a cookie is replayed
  // automatically, every unsafe method has to echo the CSRF cookie as a header.
  const unsafe = !['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(String(method).toUpperCase());
  if (auth && unsafe) {
    const csrf = getCsrfToken();
    if (csrf) headers['X-CSRFToken'] = csrf;
  }
  return headers;
};

/** Pull a human-readable message out of a DRF error body. */
const messageFrom = (data, status) => {
  if (!data) return `Request failed (${status})`;
  if (typeof data === 'string' && data.trim()) return data;
  if (data.detail) return String(data.detail);
  if (data.error) return String(data.error);
  // Field-level validation errors: { "email": ["This field is required."] }
  const fields = Object.entries(data).filter(([key]) => key !== 'code');
  if (fields.length) {
    return fields
      .map(([key, value]) => {
        const text = Array.isArray(value) ? value.join(' ') : String(value);
        return `${key}: ${text}`;
      })
      .join(' | ');
  }
  return `Request failed (${status})`;
};

export class ApiError extends Error {
  constructor(message, { status, code, data } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.data = data;
  }
}

/**
 * Perform a request and normalise success, empty bodies and errors.
 */
export const request = async (path, options = {}) => {
  const { method = 'GET', body, headers: extraHeaders, auth = true, json = true, signal } = options;

  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;
  const headers = {
    ...buildHeaders({ json: json && !isFormData, auth, method }),
    ...(extraHeaders || {}),
  };

  let res;
  try {
    res = await fetch(apiUrl(path), {
      method,
      headers,
      signal,
      // Sends the HttpOnly access-token cookie. Without this the SPA would be
      // anonymous even though it is logged in, and the app is on a different
      // origin (5173) from the API (8000), so cookies must be allowed.
      credentials: 'include',
      body: isFormData ? body : body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (cause) {
    if (cause?.name === 'AbortError') throw cause;
    throw new ApiError('Cannot reach the server. Check your connection and try again.', {
      code: 'network_error',
    });
  }

  if (res.status === 204) return null;

  const text = await res.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    throw new ApiError(messageFrom(data, res.status), {
      status: res.status,
      code: data && typeof data === 'object' ? data.code : undefined,
      data,
    });
  }
  return data;
};

/** DRF returns either a bare array or `{ results: [...] }` when paginated. */
export const asList = (data) => {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.results)) return data.results;
  if (data && Array.isArray(data.data)) return data.data;
  return [];
};
