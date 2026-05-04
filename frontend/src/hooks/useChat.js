import { useState, useCallback, useRef } from 'react';
import { sendMessage, clearChatSession } from '../services/chatbotService';

const SESSION_KEY = 'yatrip_chat_session';

export const useChat = () => {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: `Namaste! 🙏 Main **Yatrip AI Assistant** hoon.\n\nMujhse pooch sakte ho:\n- 🏨 Hotel recommendations\n- 🍽️ Local food & restaurants\n- 🏛️ Tourist attractions\n- 🚌 Transport options\n- 🏡 PG & rentals\n- ✈️ Trip planning advice\n\nKya jaanna chahte ho?`,
      timestamp: new Date().toISOString(),
      sources: [],
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const sessionIdRef = useRef(localStorage.getItem(SESSION_KEY) || null);

  const sendMsg = useCallback(async (text) => {
    if (!text.trim() || loading) return;

    const userMsg = {
      id: Date.now().toString(),
      role: 'user',
      content: text.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setError(null);

    // Optimistic typing indicator
    const typingId = 'typing_' + Date.now();
    setMessages((prev) => [...prev, { id: typingId, role: 'typing' }]);

    try {
      const res = await sendMessage(text.trim(), sessionIdRef.current);

      // Save session id
      if (res.session_id) {
        sessionIdRef.current = res.session_id;
        localStorage.setItem(SESSION_KEY, res.session_id);
      }

      const botMsg = {
        id: Date.now().toString() + '_bot',
        role: 'assistant',
        content: res.reply || res.message || 'Sorry, koi response nahi mila.',
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
    setMessages([{
      id: 'welcome_new',
      role: 'assistant',
      content: `Chat clear ho gaya! 🔄 Kya naya poochna chahte ho?`,
      timestamp: new Date().toISOString(),
      sources: [],
    }]);
    setError(null);
  }, []);

  return { messages, loading, error, sendMsg, clearChat };
};
