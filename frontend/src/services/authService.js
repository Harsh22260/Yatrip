// authService.js
import { request } from './api';

// The accounts app is mounted at /api/accounts. This used to be a hard-coded
// "http://localhost:8000/api/accounts", so every environment (staging, a phone
// on the LAN, production) silently talked to localhost.
const ACCOUNTS = 'accounts';

// ─── Session state ───────────────────────────────────────────────
// The access and refresh tokens are HttpOnly cookies set by the backend, so
// there is deliberately nothing to read or write here. `localStorage` used to
// hold them, which meant any script on the page could read the bearer token and
// act as the user until it expired.
//
// A tiny non-authoritative flag is kept in sessionStorage purely so the UI can
// avoid flashing a signed-out navbar before /profile/ has answered. Signing out
// clears it, and it grants nothing: the API decides who you are.
const SESSION_HINT = 'yatrip_session';

export const markSession = (value) => {
  try {
    if (value) sessionStorage.setItem(SESSION_HINT, '1');
    else sessionStorage.removeItem(SESSION_HINT);
  } catch {
    /* private mode - the real check is always the profile request */
  }
};

export const hasSessionHint = () => {
  try {
    return sessionStorage.getItem(SESSION_HINT) === '1';
  } catch {
    return false;
  }
};

export const clearTokens = () => markSession(false);

// ─── Auth Headers ────────────────────────────────────────────────
export const authHeaders = () => ({});

// ─── User cache ───────────────────────────────────────────────────
/**
 * The navbar and the owner pages need to know who is signed in before any
 * request completes, so the profile is cached. Previously nothing ever wrote
 * this key, so the UI always looked logged out even with a valid token.
 */
export const saveUser = (user) => {
  try {
    localStorage.setItem('user', JSON.stringify(user ?? null));
  } catch {
    /* ignore */
  }
};

export const getStoredUser = () => {
  try {
    const raw = localStorage.getItem('user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

// ─── Register ────────────────────────────────────────────────────
/**
 * `payload` may include the owner fields (business_name, business_type,
 * business_address, contact_number) alongside is_owner. The backend writes the
 * OwnerProfile in the same transaction; previously they were dropped and the
 * profile endpoint then 500'd.
 */
export const registerUser = async (payload) => request(`${ACCOUNTS}/register/`, { method: 'POST', body: payload });

// ─── Login ───────────────────────────────────────────────────────
export const loginUser = async (email, password) => {
  // The response body still carries the tokens, but they are also set as
  // HttpOnly cookies by the backend; the browser replays them from here on.
  const json = await request(`${ACCOUNTS}/login/`, {
    method: 'POST',
    body: { email, password },
    auth: false,
  });
  markSession(true);
  // Fetch the profile straight away so the UI knows the user is an owner.
  try {
    saveUser(await getUserProfile());
  } catch {
    /* profile fetch is best effort */
  }
  return json;
};

// ─── Refresh Token ───────────────────────────────────────────────
/**
 * Rotates the access token. The refresh token is read by the backend from its
 * cookie, so the SPA never handles it.
 */
export const refreshToken = async () => {
  const json = await request(`${ACCOUNTS}/token/refresh/`, {
    method: 'POST',
    body: {},
    auth: false,
  });
  markSession(true);
  return json.access;
};

// ─── Get Profile ─────────────────────────────────────────────────
export const getUserProfile = async () => {
  const user = await request(`${ACCOUNTS}/profile/`);
  saveUser(user);
  return user;
};

// ─── Owner Profile ───────────────────────────────────────────────
export const getOwnerProfile = async () => request(`${ACCOUNTS}/owner/`);

export const updateOwnerProfile = async (payload) =>
  request(`${ACCOUNTS}/owner/`, { method: 'PATCH', body: payload });

/** Upsert: creates the profile, or updates it when one already exists. */
export const createOwnerProfile = async (payload) =>
  request(`${ACCOUNTS}/owner/create/`, { method: 'POST', body: payload });

// ─── Logout ──────────────────────────────────────────────────────
// Goes through the backend rather than only clearing local state, so the
// rotating refresh token is blacklisted. Deleting a cookie alone would leave a
// copied refresh token usable until it expired.
export const logout = async () => {
  try {
    await request(`${ACCOUNTS}/logout/`, { method: 'POST', body: {} });
  } catch {
    /* the cookies are cleared regardless */
  }
  clearTokens();
  try {
    localStorage.removeItem('user');
  } catch {
    /* ignore */
  }
  window.location.href = '/login';
};
