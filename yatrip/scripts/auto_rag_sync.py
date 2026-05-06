import os
import time
import django
import logging
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yatrip.settings')
django.setup()

from django.apps import apps
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

def get_vector_store():
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=os.environ.get("GEMINI_API_KEY"),
    )
    return PineconeVectorStore(
        index_name=os.environ.get("PINECONE_INDEX_NAME", "yatrip-rag"),
        embedding=embeddings,
        pinecone_api_key=os.environ.get("PINECONE_API_KEY"),
    )

def sync_hotels():
    Hotel = apps.get_model('hotels', 'Hotel')
    hotels = Hotel.objects.all()
    docs = []
    for h in hotels:
        content = f"Hotel Name: {h.name}\nDescription: {h.description}\nAddress: {h.address}\nRating: {h.rating}"
        metadata = {"source": "hotel", "id": h.id, "title": h.name}
        docs.append(Document(page_content=content, metadata=metadata))
    return docs

def sync_food():
    FoodPlace = apps.get_model('food', 'FoodPlace')
    places = FoodPlace.objects.all()
    docs = []
    for p in places:
        content = f"Food Place: {p.name}\nCategory: {p.get_category_display()}\nCuisine: {p.get_cuisine_display()}\nAddress: {p.address}, {p.city}\nDescription: {p.description}"
        metadata = {"source": "food", "id": p.id, "title": p.name}
        docs.append(Document(page_content=content, metadata=metadata))
    return docs

def sync_attractions():
    Attraction = apps.get_model('attractions', 'Attraction')
    items = Attraction.objects.all()
    docs = []
    for a in items:
        content = f"Attraction: {a.name}\nCategory: {a.get_category_display()}\nAddress: {a.address}, {a.city}\nDescription: {a.description}"
        metadata = {"source": "attraction", "id": a.id, "title": a.name}
        docs.append(Document(page_content=content, metadata=metadata))
    return docs

def run_sync():
    print(f"[{datetime.now()}] Starting RAG Sync...")
    try:
        if not os.environ.get("PINECONE_API_KEY"):
            print("Error: PINECONE_API_KEY not found in environment.")
            return

        vs = get_vector_store()
        
        all_docs = []
        all_docs.extend(sync_hotels())
        all_docs.extend(sync_food())
        all_docs.extend(sync_attractions())

        if all_docs:
            print(f"Upserting {len(all_docs)} documents to Pinecone...")
            vs.add_documents(all_docs)
            print("Sync successful!")
        else:
            print("No data found to sync.")
            
    except Exception as e:
        print(f"Sync failed: {e}")

if __name__ == "__main__":
    # Run once at start, then every 30 minutes
    while True:
        run_sync()
        print("Waiting 30 minutes for next sync...")
        time.sleep(1800) # 30 minutes
