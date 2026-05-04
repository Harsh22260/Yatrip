import React, { useEffect, useRef, useState } from 'react';
import { useChat } from '../../hooks/useChat';
import ChatMessage from '../../components/chatbot/ChatMessage';
import ChatInput from '../../components/chatbot/ChatInput';
import QuickSuggestions from '../../components/chatbot/QuickSuggestions';
import './ChatbotPage.css';

const ChatbotPage = () => {
  const { messages, loading, error, sendMsg, clearChat } = useChat();
  const bottomRef = useRef(null);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  // Auto scroll to bottom on new message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Hide suggestions after first user message
  useEffect(() => {
    const hasUserMsg = messages.some((m) => m.role === 'user');
    if (hasUserMsg) setShowSuggestions(false);
  }, [messages]);

  const handleSend = (text) => {
    setShowSuggestions(false);
    sendMsg(text);
  };

  const handleClear = () => {
    setShowClearConfirm(false);
    clearChat();
    setShowSuggestions(true);
  };

  return (
    <div className="cbp-page">
      {/* Header */}
      <header className="cbp-header">
        <div className="cbp-header-left">
          <div className="cbp-bot-avatar">🤖</div>
          <div>
            <h1 className="cbp-title">Yatrip AI Assistant</h1>
            <div className="cbp-status">
              <span className="cbp-status-dot" />
              <span>Powered by Gemini + RAG</span>
            </div>
          </div>
        </div>

        <div className="cbp-header-actions">
          <button
            className="cbp-action-btn"
            onClick={() => setShowSuggestions(!showSuggestions)}
            title="Quick suggestions"
          >
            💡
          </button>
          <button
            className="cbp-action-btn danger"
            onClick={() => setShowClearConfirm(true)}
            title="Clear chat"
          >
            🗑️
          </button>
        </div>
      </header>

      {/* Clear Confirm Dialog */}
      {showClearConfirm && (
        <div className="cbp-confirm-overlay" onClick={() => setShowClearConfirm(false)}>
          <div className="cbp-confirm" onClick={(e) => e.stopPropagation()}>
            <h3>Chat clear karein?</h3>
            <p>Saari conversation history delete ho jayegi.</p>
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
          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Quick Suggestions */}
      <QuickSuggestions onSelect={handleSend} visible={showSuggestions} />

      {/* Input */}
      <ChatInput onSend={handleSend} loading={loading} disabled={false} />
    </div>
  );
};

export default ChatbotPage;
