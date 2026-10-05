import { asList, request } from './api';

const CHATBOT = 'chatbot';

/**
 * Anonymous sessions are protected by a secret `access_key`, not by the JWT.
 * A logged-in visitor is identified by their session id, but the key is still
 * required for anonymous history/clear calls, so it is sent whenever we have
 * one. Without it the backend answers 403 on every history call.
 */
const sessionQuery = (sessionId, accessKey) => {
  const params = new URLSearchParams();
  if (sessionId) params.set('session_id', sessionId);
  if (accessKey) params.set('access_key', accessKey);
  const query = params.toString();
  return query ? `?${query}` : '';
};

// ─── Send message to backend (multi-model chain + RAG + LangGraph) ──
export const sendMessage = async (message, sessionId = null, imageFile = null, accessKey = null) => {
  const formData = new FormData();
  formData.append('message', message ?? '');
  if (sessionId) formData.append('session_id', sessionId);
  if (accessKey) formData.append('access_key', accessKey);
  if (imageFile) formData.append('image', imageFile);

  // json:false so the helper does not force a Content-Type on FormData.
  return request(`${CHATBOT}/chat/`, { method: 'POST', body: formData, json: false });
};

// ─── Fetch chat history ─────────────────────────────────────────
export const fetchChatHistory = async (sessionId, accessKey = null) => {
  const data = await request(`${CHATBOT}/history/${sessionQuery(sessionId, accessKey)}`);
  if (Array.isArray(data)) return { messages: data, sessions: data };
  return { messages: data?.messages ?? [], ...data };
};

// ─── Fetch session list ────────────────────────────────────────
export const fetchSessionsList = async () =>
  asList(await request(`${CHATBOT}/sessions/`));

// ─── Clear a session's history ───────────────────────────────
export const clearChatSession = async (sessionId, accessKey = null) => {
  const params = {};
  if (sessionId) params.session_id = sessionId;
  if (accessKey) params.access_key = accessKey;
  return request(`${CHATBOT}/clear/`, { method: 'POST', body: params });
};
