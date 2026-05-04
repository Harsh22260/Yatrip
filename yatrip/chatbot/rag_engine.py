"""
RAG Engine — Pinecone + Google Gemini Embeddings + LangChain
============================================================
Yeh file sab kuch handle karti hai:
1. Pinecone vector store initialize karna
2. Documents ko embed karke Pinecone mein store karna
3. Query pe relevant docs retrieve karna
4. Gemini se final answer generate karna (with conversation history)
"""

import os
import logging
from typing import List, Tuple

from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_pinecone import PineconeVectorStore
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import HumanMessage, AIMessage
from langchain.prompts import PromptTemplate
from pinecone import Pinecone, ServerlessSpec

logger = logging.getLogger(__name__)

# ─── Pinecone Setup ───────────────────────────────────────
def get_pinecone_index():
    """Pinecone index initialize karo, agar nahi hai toh create karo"""
    pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
    index_name = os.environ.get("PINECONE_INDEX_NAME", "yatrip-rag")

    existing = [i.name for i in pc.list_indexes()]
    if index_name not in existing:
        pc.create_index(
            name=index_name,
            dimension=768,  # Gemini embedding-001 dimension
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        logger.info(f"Pinecone index '{index_name}' created.")

    return pc.Index(index_name), index_name


# ─── Embeddings ───────────────────────────────────────────
def get_embeddings():
    return GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=os.environ.get("GEMINI_API_KEY"),
    )


# ─── Vector Store ─────────────────────────────────────────
def get_vector_store():
    _, index_name = get_pinecone_index()
    embeddings = get_embeddings()
    return PineconeVectorStore(
        index_name=index_name,
        embedding=embeddings,
        pinecone_api_key=os.environ.get("PINECONE_API_KEY"),
    )


# ─── LLM ──────────────────────────────────────────────────
def get_llm():
    """
    Gemini 2.0 Flash — free tier best model
    Free limits: 15 RPM, 1M tokens/day
    """
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.environ.get("GEMINI_API_KEY"),
        temperature=0.7,
        convert_system_message_to_human=True,
    )


# ─── System Prompt ────────────────────────────────────────
SYSTEM_PROMPT = """
You are Yatrip AI, a smart travel assistant for the Yatrip platform.

You help users with:
- Hotels, rooms, and bookings
- Restaurants and street food
- Tourist attractions
- Transport options (bus, metro, auto, taxi)
- PG, homestay, hostels
- Trip planning and itineraries

Rules:
1. Always respond in the SAME language the user writes in.
   - If user writes in English → reply in English
   - If user writes in Hindi → reply in Hindi
   - If user writes in Hinglish → reply in Hinglish
2. Default language is English if unsure.
3. Use the context below if relevant, otherwise use your own knowledge.
4. Always give specific, helpful recommendations.
5. Show prices in Indian Rupees (₹).
6. Be concise, friendly, and accurate.

Context from Yatrip database:
{context}

Answer the user's latest question based on conversation history provided.
"""

QA_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template=SYSTEM_PROMPT + "\n\nUser ka sawaal: {question}\n\nTera jawab:"
)


# ─── Main RAG Function ────────────────────────────────────
def get_rag_response(
    query: str,
    chat_history: List[Tuple[str, str]] = None,
    top_k: int = 4,
) -> dict:
    """
    Main function — query leke RAG response deta hai

    Args:
        query: User ka message
        chat_history: List of (human, ai) tuples — conversation history
        top_k: Kitne docs retrieve karne hain

    Returns:
        { "answer": str, "sources": list }
    """
    try:
        vector_store = get_vector_store()
        llm = get_llm()
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": top_k}
        )

        # Build LangChain memory from DB history
        memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer",
            k=10,  # Last 10 exchanges yaad rakhega
        )

        if chat_history:
            for human_msg, ai_msg in chat_history:
                memory.chat_memory.add_user_message(human_msg)
                memory.chat_memory.add_ai_message(ai_msg)

        # ConversationalRetrievalChain
        chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=retriever,
            memory=memory,
            combine_docs_chain_kwargs={"prompt": QA_PROMPT},
            return_source_documents=True,
            verbose=False,
        )

        result = chain.invoke({"question": query})
        answer = result.get("answer", "Sorry, koi jawab nahi mila.")

        # Extract source names
        source_docs = result.get("source_documents", [])
        sources = list(set([
            doc.metadata.get("source", doc.metadata.get("title", "Yatrip DB"))
            for doc in source_docs
        ]))

        return {"answer": answer, "sources": sources}

    except Exception as e:
        logger.error(f"RAG error: {e}")
        # Fallback — direct LLM without RAG
        try:
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=os.environ.get("GEMINI_API_KEY"),
                temperature=0.7,
                convert_system_message_to_human=True,
            )
            fallback_prompt = f"""Tu Yatrip ka travel assistant hai.
User pooch raha hai: {query}
Helpful Hinglish mein jawab de."""
            response = llm.invoke([HumanMessage(content=fallback_prompt)])
            return {"answer": response.content, "sources": []}
        except Exception as e2:
            logger.error(f"Fallback LLM error: {e2}")
            return {"answer": "Sorry, abhi service unavailable hai. Thodi der baad try karo.", "sources": []}


# ─── Document Ingestion ───────────────────────────────────
def ingest_documents(documents: list):
    """
    Documents ko Pinecone mein store karo
    Call karo: management command se (ingest_data.py)

    documents format:
    [
        {"content": "...", "metadata": {"source": "hotels", "title": "..."}},
        ...
    ]
    """
    from langchain.schema import Document

    vector_store = get_vector_store()
    docs = [
        Document(page_content=d["content"], metadata=d.get("metadata", {}))
        for d in documents
    ]

    # Batch mein add karo (Pinecone free tier limit)
    batch_size = 100
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i + batch_size]
        vector_store.add_documents(batch)
        logger.info(f"Ingested batch {i // batch_size + 1}: {len(batch)} docs")

    return len(docs)