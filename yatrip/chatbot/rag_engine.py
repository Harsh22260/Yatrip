"""
Yatrip RAG Engine
-----------------
Gemini (LLM) + SentenceTransformers (Embeddings, local) + ChromaDB
"""
 
import os
import logging
import uuid
from typing import Optional, List
 
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.tools import DuckDuckGoSearchRun
from chromadb import EmbeddingFunction, Embeddings
import chromadb
 
logger = logging.getLogger(__name__)
 
CHROMA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")
 
 
class LocalEmbeddingFunction(EmbeddingFunction):
    """
    SentenceTransformers — 100% local, free, no API needed.
    """
    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
 
    def __call__(self, input: List[str]) -> Embeddings:
        embeddings = self.model.encode(input, convert_to_numpy=True)
        return embeddings.tolist()
 
 
def get_collection():
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    return chroma_client.get_or_create_collection(
        name="yatrip_knowledge",
        embedding_function=LocalEmbeddingFunction(),
    )
 
 
def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=os.environ.get("GEMINI_API_KEY"),
        temperature=0.3,
        convert_system_message_to_human=True,
    )
 
 
SYSTEM_PROMPT = """You are Yatrip's friendly AI travel assistant. Yatrip is an Indian travel platform that helps users discover hotels, restaurants, attractions, transport, and rentals across India.
 
Your primary goals (in order of priority):
1. Help users with Yatrip's services — hotels, food, attractions, rentals, transport bookings
2. Answer travel questions using the context provided below
3. Use web search results when Yatrip's internal data doesn't have the answer
4. Always encourage users to book through Yatrip
 
Guidelines:
- Always respond in the same language the user writes in (Hindi/English/Hinglish)
- Be friendly, helpful, and concise
- Never make up prices or availability — direct them to check on the website
 
--- YATRIP KNOWLEDGE BASE ---
{context}
 
--- WEB SEARCH RESULTS ---
{web_context}
 
--- CONVERSATION HISTORY ---
{history}
"""
 
 
def search_web(query: str) -> str:
    try:
        search = DuckDuckGoSearchRun()
        return search.run(f"India travel {query}")[:2000]
    except Exception as e:
        logger.warning(f"Web search failed: {e}")
        return ""
 
 
def get_rag_context(query: str, k: int = 4) -> str:
    try:
        collection = get_collection()
        results = collection.query(query_texts=[query], n_results=k)
        docs = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        if not docs:
            return "No specific Yatrip data found for this query."
        parts = []
        for doc, meta in zip(docs, metadatas):
            title = meta.get("title", "Info") if meta else "Info"
            parts.append(f"[{title}]\n{doc}")
        return "\n\n".join(parts)
    except Exception as e:
        logger.warning(f"RAG retrieval failed: {e}")
        return ""
 
 
def format_history(messages: list) -> str:
    if not messages:
        return "No previous conversation."
    history = []
    for msg in messages[-6:]:
        role = "User" if msg["role"] == "user" else "Yatrip Assistant"
        history.append(f"{role}: {msg['content']}")
    return "\n".join(history)
 
 
def generate_response(
    user_message: str,
    conversation_history: Optional[list] = None,
    use_web_search: bool = True,
) -> str:
    try:
        rag_context = get_rag_context(user_message)
        web_context = search_web(user_message) if use_web_search else ""
        history_str = format_history(conversation_history or [])
 
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "{question}"),
        ])
 
        chain = prompt | get_llm() | StrOutputParser()
 
        return chain.invoke({
            "context": rag_context,
            "web_context": web_context or "No web results.",
            "history": history_str,
            "question": user_message,
        })
 
    except Exception as e:
        logger.error(f"RAG generation error: {e}")
        return "Sorry, I'm having trouble right now. Please try again or contact Yatrip support!"
 
 
def ingest_text(title: str, content: str, source: str = "website", url: str = "") -> int:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", ".", " "],
    )
    chunks = splitter.split_text(content)
    if not chunks:
        return 0
 
    collection = get_collection()
    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [{"title": title, "source": source, "url": url} for _ in chunks]
    collection.add(documents=chunks, metadatas=metadatas, ids=ids)
    logger.info(f"Ingested '{title}' -> {len(chunks)} chunks")
    return len(chunks)
 
 
def ingest_url(url: str, title: str = "") -> int:
    try:
        import requests
        from bs4 import BeautifulSoup
 
        headers = {"User-Agent": "Mozilla/5.0 (compatible; YatripBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        page_title = title or (soup.title.string if soup.title else url)
        return ingest_text(page_title, text, source="website", url=url)
    except Exception as e:
        logger.error(f"URL ingest failed for {url}: {e}")
        return 0
 
 
def clear_vectorstore():
    import shutil
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)
        logger.info("ChromaDB cleared.")