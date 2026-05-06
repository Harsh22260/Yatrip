import React, { useEffect, useRef, useState } from 'react';
import { useChat } from '../../hooks/useChat';
import ChatMessage from '../../components/chatbot/ChatMessage';
import ChatInput from '../../components/chatbot/ChatInput';
import QuickSuggestions from '../../components/chatbot/QuickSuggestions';
import { fetchSessionsList } from '../../services/chatbotService';
import './ChatbotPage.css';

const ChatbotPage = () => {
  const { messages, loading, error, sendMsg, clearChat, setSessionId, loadHistory } = useChat();
  const bottomRef = useRef(null);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [isSidebarOpen, setSidebarOpen] = useState(window.innerWidth > 768);

  // Load initial history and sessions
  useEffect(() => {
    const sid = localStorage.getItem('yatrip_chat_session');
    if (sid) loadHistory(sid);
    else loadHistory(null); // Load welcome
    
    refreshSessions();
  }, [loadHistory]);

  const refreshSessions = async () => {
    try {
      const list = await fetchSessionsList();
      setSessions(list);
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    const hasUserMsg = messages.some((m) => m.role === 'user');
    if (hasUserMsg) setShowSuggestions(false);
  }, [messages]);

  const handleSend = async (text, image) => {
    setShowSuggestions(false);
    await sendMsg(text, image);
    refreshSessions();
  };

  const handleClear = () => {
    setShowClearConfirm(false);
    clearChat();
    setShowSuggestions(true);
    setSessions([]);
  };

  const handleSelectSession = (sid) => {
    setSessionId(sid);
    if (window.innerWidth <= 768) setSidebarOpen(false);
  };

  return (
    <div className={`cbp-container ${isSidebarOpen ? 'sidebar-open' : ''}`}>
      {/* Sidebar */}
      <aside className="cbp-sidebar">
        <div className="cbp-sidebar-header">
          <button className="cbp-new-chat" onClick={() => clearChat()}>
            <span>+</span> New Chat
          </button>
        </div>
        <div className="cbp-session-list">
          <h3>Recent Chats</h3>
          {sessions.length === 0 && <p className="cbp-no-sessions">No recent chats</p>}
          {sessions.map(s => (
            <div 
              key={s.session_id} 
              className={`cbp-session-item ${localStorage.getItem('yatrip_chat_session') === s.session_id ? 'active' : ''}`}
              onClick={() => handleSelectSession(s.session_id)}
            >
              <span className="cbp-session-icon">💬</span>
              <div className="cbp-session-info">
                <p>{s.last_message || 'New Chat'}</p>
                <small>{new Date(s.updated_at).toLocaleDateString()}</small>
              </div>
            </div>
          ))}
        </div>
      </aside>

      <div className="cbp-page">
        {/* Header */}
        <header className="cbp-header">
          <div className="cbp-header-left">
            <button className="cbp-toggle-sidebar" onClick={() => setSidebarOpen(!isSidebarOpen)}>
              ☰
            </button>
            <div className="cbp-bot-avatar">🤖</div>
            <div>
              <h1 className="cbp-title">Yatrip AI</h1>
              <div className="cbp-status">
                <span className="cbp-status-dot" />
                <span>Online · Advanced RAG Agent</span>
              </div>
            </div>
          </div>

          <div className="cbp-header-actions">
            <button className="cbp-action-btn" onClick={() => setShowSuggestions(!showSuggestions)} title="Suggestions">
              💡
            </button>
            <button className="cbp-action-btn danger" onClick={() => setShowClearConfirm(true)} title="Clear chat">
              🗑️
            </button>
          </div>
        </header>

        {/* Clear Confirm Dialog */}
        {showClearConfirm && (
          <div className="cbp-confirm-overlay" onClick={() => setShowClearConfirm(false)}>
            <div className="cbp-confirm" onClick={(e) => e.stopPropagation()}>
              <h3>Clear history?</h3>
              <p>This will delete all messages in this session.</p>
              <div className="cbp-confirm-actions">
                <button className="cbp-confirm-cancel" onClick={() => setShowClearConfirm(false)}>Cancel</button>
                <button className="cbp-confirm-ok" onClick={handleClear}>Clear</button>
              </div>
            </div>
          </div>
        )}

        {/* Messages area */}
        <div className="cbp-messages">
          <div className="cbp-messages-inner">
            {messages.length === 0 && !loading && (
              <div className="cbp-welcome-screen">
                <div className="cbp-welcome-bot">🤖</div>
                <h2>Namaste! Main Yatrip AI hoon.</h2>
                <p>Aap mujhse trip planning, hotels, ya attractions ke baare me pooch sakte hain.</p>
              </div>
            )}
            {messages.map((msg) => (
              <ChatMessage key={msg.id || Math.random()} message={msg} />
            ))}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Quick Suggestions */}
        <QuickSuggestions onSelect={handleSend} visible={showSuggestions} />

        {/* Input */}
        <ChatInput onSend={handleSend} loading={loading} disabled={false} />
      </div>
    </div>
  );
};

export default ChatbotPage;
