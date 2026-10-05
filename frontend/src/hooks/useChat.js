import { useCallback, useEffect, useRef, useState } from 'react';
import { clearChatSession, fetchChatHistory, sendMessage } from '../services/chatbotService';

const SESSION_KEY = 'yatrip_chat_session';
const ACCESS_KEY = 'yatrip_chat_access_key';

const readStored = (key) => {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
};

const WELCOME = `Namaste! 🙏 Main **Yatrip AI Assistant** hoon.

Mujhse pooch sakte ho:
- 🏨 Hotel recommendations
- 🍽️ Local food & restaurants
- 🏛️ Tourist attractions
- 🚌 Transport options
- 🏡 PG & rentals
- ✈️ Trip planning advice

Kya jaanna chahte ho?`;

const welcomeMsg = () => ({
  id: 'welcome',
  role: 'assistant',
  content: WELCOME,
  timestamp: new Date().toISOString(),
  sources: [],
});

export const useChat = () => {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionId, setSessionIdState] = useState(() => readStored(SESSION_KEY));
  const [accessKey, setAccessKeyState] = useState(() => readStored(ACCESS_KEY));

  // A ref keeps the access key readable inside callbacks without making them
  // re-create on every render.
  const accessKeyRef = useRef(accessKey);
  const sessionIdRef = useRef(sessionId);
  accessKeyRef.current = accessKey;
  sessionIdRef.current = sessionId;

  useEffect(() => {
    setMessages([welcomeMsg()]);
  }, []);

  const loadHistory = useCallback(async (sid = sessionIdRef.current, key = accessKeyRef.current) => {
    if (!sid) return;
    setLoading(true);
    try {
      const data = await fetchChatHistory(sid, key);
      if (data.messages?.length) {
        setMessages(data.messages);
      } else {
        setMessages([welcomeMsg()]);
      }
    } catch {
      // A missing/expired session is not worth shouting about; start fresh.
      setMessages([welcomeMsg()]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Restore the previous conversation on mount. Previously this never ran and
  // the thread was empty on every page load.
  useEffect(() => {
    if (sessionIdRef.current) loadHistory();
  }, [loadHistory]);

  const persistSession = useCallback((nextId, nextKey) => {
    if (nextId) {
      sessionIdRef.current = nextId;
      setSessionIdState(nextId);
      try {
        localStorage.setItem(SESSION_KEY, nextId);
      } catch {
        /* ignore */
      }
    }
    if (nextKey) {
      accessKeyRef.current = nextKey;
      setAccessKeyState(nextKey);
      try {
        localStorage.setItem(ACCESS_KEY, nextKey);
      } catch {
        /* ignore */
      }
    }
  }, []);

  const sendMsg = useCallback(
    async (text, imageFile = null) => {
      const trimmed = (text || '').trim();
      if (!trimmed && !imageFile) return;
      if (loading) return;

      const userMsg = {
        id: `u_${Date.now()}`,
        role: 'user',
        content: trimmed || (imageFile ? 'Analyzed Image' : ''),
        image: imageFile ? URL.createObjectURL(imageFile) : null,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);
      setError(null);

      const typingId = `typing_${Date.now()}`;
      setMessages((prev) => [...prev, { id: typingId, role: 'typing' }]);

      try {
        const res = await sendMessage(trimmed, sessionIdRef.current, imageFile, accessKeyRef.current);
        persistSession(res.session_id, res.access_key);

        const botMsg = {
          id: `a_${Date.now()}`,
          role: 'assistant',
          content: res.reply || res.answer || 'Sorry, koi response nahi mila.',
          timestamp: new Date().toISOString(),
          sources: res.sources || [],
        };
        setMessages((prev) => prev.filter((m) => m.id !== typingId).concat(botMsg));
      } catch (e) {
        setError(e.message);
        setMessages((prev) =>
          prev.filter((m) => m.id !== typingId).concat({
            id: `e_${Date.now()}`,
            role: 'error',
            content: `⚠️ ${e.message}`,
            timestamp: new Date().toISOString(),
          })
        );
      } finally {
        setLoading(false);
      }
    },
    [loading, persistSession]
  );

  const clearChat = useCallback(async () => {
    try {
      if (sessionIdRef.current) {
        await clearChatSession(sessionIdRef.current, accessKeyRef.current);
      }
    } catch {
      /* the local thread is reset regardless */
    }
    sessionIdRef.current = null;
    accessKeyRef.current = null;
    setSessionIdState(null);
    setAccessKeyState(null);
    try {
      localStorage.removeItem(SESSION_KEY);
      localStorage.removeItem(ACCESS_KEY);
    } catch {
      /* ignore */
    }
    setMessages([welcomeMsg()]);
    setError(null);
  }, []);

  const setSessionId = useCallback(
    (sid, key) => {
      persistSession(sid, key);
      setMessages([welcomeMsg()]);
      setError(null);
      if (sid) loadHistory(sid, key ?? accessKeyRef.current);
    },
    [persistSession, loadHistory]
  );

  return { messages, loading, error, sessionId, sendMsg, clearChat, setSessionId, loadHistory };
};
