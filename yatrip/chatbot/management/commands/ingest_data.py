"""
python manage.py ingest_data              # sab ingest
python manage.py ingest_data --model hotels
python manage.py ingest_data --model attractions
python manage.py ingest_data --model food
python manage.py ingest_data --model rentals
python manage.py ingest_data --model transport
"""

import os
import logging
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


def ingest_documents(documents: list) -> int:
    """Pinecone mein documents store karo"""
    if not documents:
        return 0

    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from langchain_pinecone import PineconeVectorStore
    from langchain.schema import Document
    from pinecone import Pinecone, ServerlessSpec

    # Init Pinecone index
    pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY", ""))
    index_name = os.environ.get("PINECONE_INDEX_NAME", "yatrip-rag")
    existing = [i.name for i in pc.list_indexes()]
    if index_name not in existing:
        pc.create_index(
            name=index_name,
            dimension=768,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=os.environ.get("GEMINI_API_KEY", ""),
    )
    vs = PineconeVectorStore(
        index_name=index_name,
        embedding=embeddings,
        pinecone_api_key=os.environ.get("PINECONE_API_KEY", ""),
    )

    docs = [
        Document(page_content=d["content"], metadata=d.get("metadata", {}))
        for d in documents
    ]

    batch_size = 100
    for i in range(0, len(docs), batch_size):
        vs.add_documents(docs[i:i + batch_size])

    return len(docs)


class Command(BaseCommand):
    help = 'Yatrip data ko Pinecone vector store mein ingest karo'

    def add_arguments(self, parser):
        parser.add_argument('--model', type=str, default='all',
            help='all | hotels | attractions | food | rentals | transport')

    def handle(self, *args, **options):
        model = options['model']
        total = 0

        if model in ('all', 'hotels'):       total += self._ingest_hotels()
        if model in ('all', 'attractions'):  total += self._ingest_attractions()
        if model in ('all', 'food'):         total += self._ingest_food()
        if model in ('all', 'rentals'):      total += self._ingest_rentals()
        if model in ('all', 'transport'):    total += self._ingest_transport()

        self.stdout.write(self.style.SUCCESS(f'✅ Total {total} documents ingested!'))

    def _ingest_hotels(self):
        from hotels.models import Hotel
        self.stdout.write('🏨 Hotels...')
        docs = []
        for h in Hotel.objects.prefetch_related('room_types').all():
            rooms = "\n".join([
                f"  - {r.name}: ₹{r.base_price}/night, capacity {r.capacity}, {r.total_units} units"
                for r in h.room_types.all()
            ])
            docs.append({
                "content": f"Hotel: {h.name}\nAddress: {h.address}\nRating: {h.rating}/5\n"
                           f"Verified: {'Yes' if h.is_verified else 'No'}\n"
                           f"Description: {h.description or 'N/A'}\nRooms:\n{rooms or 'N/A'}",
                "metadata": {"source": "hotels", "title": h.name, "hotel_id": str(h.id)},
            })
        count = ingest_documents(docs)
        self.stdout.write(f'  ✓ {count} hotel docs')
        return count

    def _ingest_attractions(self):
        from attractions.models import Attraction
        self.stdout.write('🏛️ Attractions...')
        docs = []
        for a in Attraction.objects.all():
            docs.append({
                "content": f"Attraction: {a.name}\nCity: {a.city}\nCategory: {a.get_category_display()}\n"
                           f"Address: {a.address or 'N/A'}\n"
                           f"Entry Fee: {'Free' if a.entry_fee == 0 else f'₹{a.entry_fee}'}\n"
                           f"Timings: {a.opening_time or 'N/A'} - {a.closing_time or 'N/A'}\n"
                           f"Description: {a.description or 'N/A'}",
                "metadata": {"source": "attractions", "title": a.name, "city": a.city},
            })
        count = ingest_documents(docs)
        self.stdout.write(f'  ✓ {count} attraction docs')
        return count

    def _ingest_food(self):
        from food.models import FoodVendor
        self.stdout.write('🍽️ Food vendors...')
        docs = []
        for v in FoodVendor.objects.prefetch_related('menu_items').select_related('category').all():
            menu = "\n".join([
                f"  - {i.name}: ₹{i.price}"
                for i in v.menu_items.filter(is_available=True)[:10]
            ])
            docs.append({
                "content": f"Food Vendor: {v.name}\nType: {v.get_vendor_type_display()}\n"
                           f"Category: {v.category.name if v.category else 'N/A'}\n"
                           f"Address: {v.address}\nAvg Cost: ₹{v.avg_cost}\nRating: {v.rating}/5\n"
                           f"Description: {v.description or 'N/A'}\nMenu:\n{menu or 'N/A'}",
                "metadata": {"source": "food", "title": v.name},
            })
        count = ingest_documents(docs)
        self.stdout.write(f'  ✓ {count} food docs')
        return count

    def _ingest_rentals(self):
        from rentals.models import Rental
        self.stdout.write('🏡 Rentals...')
        docs = []
        for r in Rental.objects.prefetch_related('amenities').all():
            amenities = ', '.join([a.name for a in r.amenities.all()]) or 'None'
            docs.append({
                "content": f"Rental: {r.name}\nType: {r.get_rental_type_display()}\n"
                           f"Address: {r.address}\nPrice: ₹{r.price_per_month}/month\n"
                           f"Rooms Available: {r.available_rooms}\n"
                           f"Verified: {'Yes' if r.is_verified else 'No'}\n"
                           f"Amenities: {amenities}\nDescription: {r.description or 'N/A'}",
                "metadata": {"source": "rentals", "title": r.name},
            })
        count = ingest_documents(docs)
        self.stdout.write(f'  ✓ {count} rental docs')
        return count

    def _ingest_transport(self):
        from transport.models import TransportNode
        self.stdout.write('🚌 Transport...')
        docs = []
        for t in TransportNode.objects.all():
            docs.append({
                "content": f"Transport: {t.name}\nType: {t.get_node_type_display()}\n"
                           f"City: {t.city}\nAddress: {t.address or 'N/A'}",
                "metadata": {"source": "transport", "title": t.name, "city": t.city},
            })
        count = ingest_documents(docs)
        self.stdout.write(f'  ✓ {count} transport docs')
        return count