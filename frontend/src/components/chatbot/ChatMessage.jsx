import React from 'react';
import { parseMarkdown, formatTime } from '../../utils/chatHelpers';
import './ChatMessage.css';

const TypingIndicator = () => (
  <div className="cm-wrap cm-assistant">
    <div className="cm-avatar bot">🤖</div>
    <div className="cm-bubble typing">
      <span className="cm-dot" /><span className="cm-dot" /><span className="cm-dot" />
    </div>
  </div>
);

const ChatMessage = ({ message }) => {
  if (message.role === 'typing') return <TypingIndicator />;

  const isUser = message.role === 'user';
  const isError = message.role === 'error';

  return (
    <div className={`cm-wrap ${isUser ? 'cm-user' : 'cm-assistant'}`}>
      {!isUser && (
        <div className={`cm-avatar ${isError ? 'error' : 'bot'}`}>
          {isError ? '⚠️' : '🤖'}
        </div>
      )}

      <div className={`cm-content ${isUser ? 'user' : isError ? 'error' : 'bot'}`}>
        <div
          className="cm-bubble"
          dangerouslySetInnerHTML={{ __html: parseMarkdown(message.content) }}
        />
        
        {message.image_url && (
          <div className="cm-image-wrap">
            <img src={message.image_url} alt="User upload" onClick={() => window.open(message.image_url, '_blank')} />
          </div>
        )}

        {/* Sources from RAG */}
        {message.sources?.length > 0 && (
          <div className="cm-sources">
            <span className="cm-sources-label">📚 Sources:</span>
            {message.sources.map((src, i) => (
              <span key={i} className="cm-source-chip">{src}</span>
            ))}
          </div>
        )}

        <span className="cm-time">{formatTime(message.timestamp)}</span>
      </div>

      {isUser && (
        <div className="cm-avatar user">👤</div>
      )}
    </div>
  );
};

export default ChatMessage;
