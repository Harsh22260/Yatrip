const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const getAuthHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('access_token')}`,
});

// ─── Send message to backend (Gemini + RAG + LangChain) ──
export const sendMessage = async (message, sessionId = null) => {
  const res = await fetch(`${BASE_URL}/chatbot/chat/`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || 'Chat failed');
  }
  return res.json();
  // Expected response: { reply: "...", session_id: "...", sources: [...] }
};

// ─── Fetch chat history ───────────────────────────────────
export const fetchChatHistory = async (sessionId) => {
  const res = await fetch(
    `${BASE_URL}/chatbot/history/?session_id=${sessionId}`,
    { headers: getAuthHeaders() }
  );
  if (!res.ok) throw new Error('History fetch failed');
  return res.json();
};

// ─── Clear session ────────────────────────────────────────
export const clearChatSession = async (sessionId) => {
  const res = await fetch(`${BASE_URL}/chatbot/clear/`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!res.ok) throw new Error('Clear failed');
  return res.json();
};
