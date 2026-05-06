export const parseMarkdown = (text) => {
  if (!text) return '';
  let html = text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/^### (.*$)/gm, '<h3>$1</h3>')
    .replace(/^## (.*$)/gm, '<h2>$1</h2>');

  // Better list handling
  const lines = html.split('\n');
  let inList = false;
  let finalHtml = '';

  lines.forEach(line => {
    if (line.trim().startsWith('- ')) {
      if (!inList) {
        finalHtml += '<ul>';
        inList = true;
      }
      finalHtml += `<li>${line.trim().substring(2)}</li>`;
    } else {
      if (inList) {
        finalHtml += '</ul>';
        inList = false;
      }
      finalHtml += line + '<br/>';
    }
  });

  if (inList) finalHtml += '</ul>';
  return finalHtml;
};

export const formatTime = (isoStr) => {
  if (!isoStr) return '';
  return new Date(isoStr).toLocaleTimeString('en-IN', {
    hour: '2-digit', minute: '2-digit',
  });
};

export const QUICK_SUGGESTIONS = [
  { label: '🏨 Delhi Hotels', text: 'Best hotels in Delhi under ₹3000?' },
  { label: '🍽️ Street Food', text: 'Top 5 street food places in Mumbai?' },
  { label: '🏛️ Taj Mahal Trip', text: 'How to plan a Taj Mahal trip from Delhi?' },
  { label: '🚌 Transport', text: 'Intercity bus options from Bangalore to Coorg?' },
  { label: '🌄 Hill Stations', text: 'Beautiful hill stations near Pune for weekend?' },
];
