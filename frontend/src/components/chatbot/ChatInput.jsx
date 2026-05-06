import React, { useState, useRef, useEffect } from 'react';
import './ChatInput.css';

const ChatInput = ({ onSend, loading, disabled }) => {
  const [value, setValue] = useState('');
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 140) + 'px';
    }
  }, [value]);

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImage(file);
      setImagePreview(URL.createObjectURL(file));
    }
  };

  const removeImage = () => {
    setImage(null);
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleSend = () => {
    if ((!value.trim() && !image) || loading || disabled) return;
    onSend(value.trim(), image);
    setValue('');
    removeImage();
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="ci-wrap">
      {imagePreview && (
        <div className="ci-preview">
          <img src={imagePreview} alt="Preview" />
          <button className="ci-remove-img" onClick={removeImage}>✕</button>
        </div>
      )}
      <div className={`ci-box ${loading ? 'loading' : ''}`}>
        <button className="ci-attach-btn" onClick={() => fileInputRef.current?.click()} title="Upload Image">
          📎
        </button>
        <input 
          type="file" 
          ref={fileInputRef} 
          hidden 
          accept="image/*" 
          onChange={handleImageChange} 
        />
        <textarea
          ref={textareaRef}
          className="ci-input"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Kuch bhi poochho — trip planning, hotels, food..."
          rows={1}
          disabled={disabled}
        />
        <button
          className={`ci-send-btn ${(value.trim() || image) && !loading ? 'active' : ''}`}
          onClick={handleSend}
          disabled={(!value.trim() && !image) || loading || disabled}
          title="Send (Enter)"
        >
          {loading ? (
            <span className="ci-spinner" />
          ) : (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          )}
        </button>
      </div>
      <p className="ci-hint">Enter to send · Shift+Enter for new line</p>
    </div>
  );
};

export default ChatInput;
