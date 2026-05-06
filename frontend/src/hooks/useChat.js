import { useState, useCallback, useRef } from 'react';
import { sendMessage, clearChatSession } from '../services/chatbotService';

const SESSION_KEY = 'yatrip_chat_session';

export const useChat = () => {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const sessionIdRef = useRef(localStorage.getItem(SESSION_KEY) || null);

  const welcomeMsg = {
    id: 'welcome',
    role: 'assistant',
    content: `Namaste! 🙏 Main **Yatrip AI Assistant** hoon.\n\nMujhse pooch sakte ho:\n- 🏨 Hotel recommendations\n- 🍽️ Local food & restaurants\n- 🏛️ Tourist attractions\n- 🚌 Transport options\n- 🏡 PG & rentals\n- ✈️ Trip planning advice\n\nKya jaanna chahte ho?`,
    timestamp: new Date().toISOString(),
    sources: [],
  };

  // Load history if session exists
  const loadHistory = useCallback(async (sid) => {
    setLoading(true);
    try {
      const data = await fetchChatHistory(sid);
      if (data.messages && data.messages.length > 0) {
        setMessages(data.messages);
      } else {
        setMessages([welcomeMsg]);
      }
    } catch (e) {
      setMessages([welcomeMsg]);
    } finally {
      setLoading(false);
    }
  }, []);

  const sendMsg = useCallback(async (text, imageFile = null) => {
    if (!text.trim() && !imageFile) return;
    if (loading) return;

    const userMsg = {
      id: Date.now().toString(),
      role: 'user',
      content: text.trim() || (imageFile ? 'Analyzed Image' : ''),
      image: imageFile ? URL.createObjectURL(imageFile) : null,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setError(null);

    const typingId = 'typing_' + Date.now();
    setMessages((prev) => [...prev, { id: typingId, role: 'typing' }]);

    try {
      const res = await sendMessage(text.trim(), sessionIdRef.current, imageFile);

      if (res.session_id) {
        sessionIdRef.current = res.session_id;
        localStorage.setItem(SESSION_KEY, res.session_id);
      }

      const botMsg = {
        id: Date.now().toString() + '_bot',
        role: 'assistant',
        content: res.reply || 'Sorry, koi response nahi mila.',
        timestamp: new Date().toISOString(),
        sources: res.sources || [],
      };

      setMessages((prev) => prev.filter((m) => m.id !== typingId).concat(botMsg));
    } catch (e) {
      setError(e.message);
      setMessages((prev) => prev.filter((m) => m.id !== typingId).concat({
        id: Date.now().toString() + '_err',
        role: 'error',
        content: `⚠️ ${e.message}. Please try again.`,
        timestamp: new Date().toISOString(),
      }));
    } finally {
      setLoading(false);
    }
  }, [loading]);

  const clearChat = useCallback(async () => {
    try {
      if (sessionIdRef.current) await clearChatSession(sessionIdRef.current);
    } catch (_) {}
    sessionIdRef.current = null;
    localStorage.removeItem(SESSION_KEY);
    setMessages([welcomeMsg]);
    setError(null);
  }, []);

  const setSessionId = (sid) => {
    sessionIdRef.current = sid;
    localStorage.setItem(SESSION_KEY, sid);
    loadHistory(sid);
  };

  return { messages, loading, error, sendMsg, clearChat, setSessionId, loadHistory };
};
