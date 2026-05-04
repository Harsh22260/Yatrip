// ─── Simple Markdown → HTML ───────────────────────────────
export const parseMarkdown = (text) => {
  if (!text) return '';
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/^### (.*$)/gm, '<h3>$1</h3>')
    .replace(/^## (.*$)/gm, '<h2>$1</h2>')
    .replace(/^- (.*$)/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br/>');
};

// ─── Timestamp formatter ──────────────────────────────────
export const formatTime = (isoStr) => {
  if (!isoStr) return '';
  return new Date(isoStr).toLocaleTimeString('en-IN', {
    hour: '2-digit', minute: '2-digit',
  });
};

// ─── Quick Suggestions ────────────────────────────────────
export const QUICK_SUGGESTIONS = [
  { label: '🏨 Best hotels in Delhi', text: 'Best hotels in Delhi under ₹3000 per night?' },
  { label: '🍽️ Street food near me', text: 'Famous street food places near me?' },
  { label: '🏛️ Top attractions', text: 'Top tourist attractions in Agra?' },
  { label: '🚌 Transport options', text: 'How to travel from Delhi to Jaipur?' },
  { label: '🏡 PG in Mumbai', text: 'Affordable PGs in Mumbai with WiFi?' },
  { label: '✈️ Plan my trip', text: 'Plan a 3-day trip to Rajasthan for 2 people' },
];

// ─── Typing animation dots ────────────────────────────────
export const TYPING_DOTS = '...';
