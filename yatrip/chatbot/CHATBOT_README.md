# Yatrip AI Chatbot — Setup Guide

## Tech Stack
- **LLM**: Google Gemini 1.5 Flash (Free tier)
- **RAG**: LangChain + ChromaDB
- **Web Search**: DuckDuckGo (Free, no API key)
- **Embeddings**: Google Generative AI Embeddings (Free)

---

## Step 1: Install Dependencies

```bash
pip install langchain langchain-google-genai langchain-chroma langchain-community chromadb beautifulsoup4 requests duckduckgo-search
```

---

## Step 2: Get Gemini API Key (FREE)

1. Go to: https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key

---

## Step 3: .env file mein add karo

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## Step 4: Files copy karo

Apne project ke `chatbot/` folder mein ye files copy karo:
- `models.py`
- `views.py`
- `urls.py`
- `rag_engine.py`
- `migrations/0001_initial.py`
- `management/commands/ingest_data.py`

---

## Step 5: Main urls.py mein add karo

```python
# yatrip/urls.py
path("api/chatbot/", include("chatbot.urls")),
```

---

## Step 6: Migrations run karo

```bash
python manage.py makemigrations chatbot
python manage.py migrate
```

---

## Step 7: Data Ingest karo

```bash
# Yatrip base knowledge + DB data ingest karo
python manage.py ingest_data

# Sirf base knowledge
python manage.py ingest_data --base-only

# Apni website ka koi specific page
python manage.py ingest_data --url https://yatrip.com/about

# ChromaDB clear karna ho to
python manage.py ingest_data --clear
```

---

## API Endpoints

### 1. Chat
```
POST /api/chatbot/chat/
Content-Type: application/json

{
  "message": "Delhi mein best hotels kaunse hain?",
  "conversation_id": null,     // optional - pehli baar null bhejo
  "session_id": "abc123"       // optional - guest users ke liye
}

Response:
{
  "response": "Delhi mein Yatrip par ye top hotels hain...",
  "conversation_id": 1,
  "session_id": "abc123"
}
```

### 2. Conversation History
```
GET /api/chatbot/history/1/

Response:
{
  "messages": [
    {"role": "user", "content": "...", "created_at": "..."},
    {"role": "assistant", "content": "...", "created_at": "..."}
  ]
}
```

### 3. Clear Conversation
```
DELETE /api/chatbot/clear/1/
```

---

## Deployment (Railway - Free)

1. `railway login`
2. `railway init`
3. Environment variable add karo: `GEMINI_API_KEY`
4. `railway up`

### Procfile (root mein banao):
```
web: gunicorn yatrip.wsgi:application
release: python manage.py migrate && python manage.py ingest_data --base-only
```

---

## How RAG Works

```
User Message
     ↓
ChromaDB mein similarity search (Yatrip's own data)
     ↓
DuckDuckGo web search (internet se current info)
     ↓
Conversation history (context ke liye)
     ↓
Gemini 1.5 Flash (sab combine karke response)
     ↓
User ko response
```

Priority order:
1. Yatrip ki internal data (hotels, attractions, food, rentals)
2. Internet se travel info
3. General Gemini knowledge

---

## Naya Data Add Karna

```python
# Kisi bhi view ya script mein:
from chatbot.rag_engine import ingest_text, ingest_url

# Text directly add karo
ingest_text(
    title="Manali Travel Guide",
    content="Manali ek beautiful hill station hai...",
    source="custom"
)

# URL se scrape karke add karo
ingest_url("https://incredibleindia.org/manali")
```
