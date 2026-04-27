// authService.js
const API_BASE = "http://localhost:8000/api/accounts";
 
// ─── Token Helpers ───────────────────────────────────────────────
export const saveTokens = (access, refresh) => {
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
};
 
export const getAccessToken = () => localStorage.getItem("access_token");
export const getRefreshToken = () => localStorage.getItem("refresh_token");
 
export const clearTokens = () => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
};
 
export const isLoggedIn = () => !!getAccessToken();
 
// ─── Auth Headers ────────────────────────────────────────────────
export const authHeaders = () => ({
  "Content-Type": "application/json",
  Authorization: `Bearer ${getAccessToken()}`,
});
 
// ─── Register ────────────────────────────────────────────────────
export const registerUser = async (data) => {
  const res = await fetch(`${API_BASE}/register/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  const json = await res.json();
  if (!res.ok) throw json;
  return json;
};
 
// ─── Login ───────────────────────────────────────────────────────
export const loginUser = async (email, password) => {
  const res = await fetch(`${API_BASE}/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const json = await res.json();
  if (!res.ok) throw json;
  saveTokens(json.access, json.refresh);
  return json;
};
 
// ─── Refresh Token ───────────────────────────────────────────────
export const refreshToken = async () => {
  const res = await fetch(`${API_BASE}/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: getRefreshToken() }),
  });
  const json = await res.json();
  if (!res.ok) { clearTokens(); throw json; }
  localStorage.setItem("access_token", json.access);
  return json.access;
};
 
// ─── Get Profile ─────────────────────────────────────────────────
export const getUserProfile = async () => {
  const res = await fetch(`${API_BASE}/profile/`, {
    headers: authHeaders(),
  });
  const json = await res.json();
  if (!res.ok) throw json;
  return json;
};
 
// ─── Get Owner Profile ───────────────────────────────────────────
export const getOwnerProfile = async () => {
  const res = await fetch(`${API_BASE}/owner/`, {
    headers: authHeaders(),
  });
  const json = await res.json();
  if (!res.ok) throw json;
  return json;
};
 
// ─── Logout ──────────────────────────────────────────────────────
export const logout = () => {
  clearTokens();
  window.location.href = "/login";
};