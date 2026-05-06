from django.core.management.base import BaseCommand
import os
import time
from datetime import datetime
from django.apps import apps
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document

class Command(BaseCommand):
    help = 'Sync Django models (Hotels, Food, Attractions) to Pinecone Vector DB'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f"[{datetime.now()}] Starting RAG Sync..."))
        
        try:
            if not os.environ.get("PINECONE_API_KEY"):
                self.stdout.write(self.style.ERROR("Error: PINECONE_API_KEY not found in environment."))
                return

            embeddings = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=os.environ.get("GEMINI_API_KEY"),
            )
            vs = PineconeVectorStore(
                index_name=os.environ.get("PINECONE_INDEX_NAME", "yatrip-rag"),
                embedding=embeddings,
                pinecone_api_key=os.environ.get("PINECONE_API_KEY"),
            )

            all_docs = []
            
            # Sync Hotels
            Hotel = apps.get_model('hotels', 'Hotel')
            for h in Hotel.objects.all():
                content = f"Hotel: {h.name}\nDescription: {h.description}\nAddress: {h.address}\nRating: {h.rating}"
                all_docs.append(Document(page_content=content, metadata={"source": "hotel", "id": h.id, "title": h.name}))

            # Sync Food
            FoodPlace = apps.get_model('food', 'FoodPlace')
            for p in FoodPlace.objects.all():
                content = f"Food Place: {p.name}\nCuisine: {p.cuisine}\nAddress: {p.address}, {p.city}\nDescription: {p.description}"
                all_docs.append(Document(page_content=content, metadata={"source": "food", "id": p.id, "title": p.name}))

            # Sync Attractions
            Attraction = apps.get_model('attractions', 'Attraction')
            for a in Attraction.objects.all():
                content = f"Attraction: {a.name}\nAddress: {a.address}, {a.city}\nDescription: {a.description}"
                all_docs.append(Document(page_content=content, metadata={"source": "attraction", "id": a.id, "title": a.name}))

            if all_docs:
                self.stdout.write(f"Upserting {len(all_docs)} documents to Pinecone...")
                vs.add_documents(all_docs)
                self.stdout.write(self.style.SUCCESS("Sync successful!"))
            else:
                self.stdout.write("No data found to sync.")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Sync failed: {e}"))
