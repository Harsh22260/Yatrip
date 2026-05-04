"""
Management Command: ingest_data
================================
Yatrip ke saare models ka data Pinecone vector store mein ingest karta hai.

Usage:
    python manage.py ingest_data              # Sab ingest karo
    python manage.py ingest_data --model hotels
    python manage.py ingest_data --model attractions
    python manage.py ingest_data --model food
    python manage.py ingest_data --model rentals
"""

from django.core.management.base import BaseCommand
from chatbot.rag_engine import ingest_documents


class Command(BaseCommand):
    help = 'Yatrip data ko Pinecone vector store mein ingest karo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            default='all',
            help='Kaunsa model ingest karna hai: all, hotels, attractions, food, rentals, transport'
        )

    def handle(self, *args, **options):
        model = options['model']
        total = 0

        if model in ('all', 'hotels'):
            total += self._ingest_hotels()

        if model in ('all', 'attractions'):
            total += self._ingest_attractions()

        if model in ('all', 'food'):
            total += self._ingest_food()

        if model in ('all', 'rentals'):
            total += self._ingest_rentals()

        if model in ('all', 'transport'):
            total += self._ingest_transport()

        self.stdout.write(self.style.SUCCESS(f'✅ Total {total} documents ingested successfully!'))

    # ─── HOTELS ───────────────────────────────────────────
    def _ingest_hotels(self):
        from hotels.models import Hotel, RoomType

        self.stdout.write('🏨 Hotels ingesting...')
        docs = []

        for hotel in Hotel.objects.prefetch_related('room_types').all():
            room_info = ""
            for room in hotel.room_types.all():
                room_info += f"\n  - {room.name}: ₹{room.base_price}/night, capacity: {room.capacity}, units: {room.total_units}"

            content = f"""Hotel: {hotel.name}
Address: {hotel.address}
Rating: {hotel.rating}/5
Verified: {'Yes' if hotel.is_verified else 'No'}
Description: {hotel.description or 'N/A'}
Room Types:{room_info if room_info else ' No rooms listed'}"""

            docs.append({
                "content": content,
                "metadata": {
                    "source": "hotels",
                    "title": hotel.name,
                    "hotel_id": str(hotel.id),
                    "address": hotel.address,
                }
            })

        count = ingest_documents(docs)
        self.stdout.write(f'  ✓ {count} hotel documents ingested')
        return count

    # ─── ATTRACTIONS ──────────────────────────────────────
    def _ingest_attractions(self):
        from attractions.models import Attraction

        self.stdout.write('🏛️ Attractions ingesting...')
        docs = []

        for a in Attraction.objects.all():
            content = f"""Tourist Attraction: {a.name}
City: {a.city}
Category: {a.get_category_display()}
Address: {a.address or 'N/A'}
Entry Fee: {'Free' if a.entry_fee == 0 else f'₹{a.entry_fee}'}
Timings: {a.opening_time or 'N/A'} - {a.closing_time or 'N/A'}
Description: {a.description or 'N/A'}"""

            docs.append({
                "content": content,
                "metadata": {
                    "source": "attractions",
                    "title": a.name,
                    "attraction_id": str(a.id),
                    "city": a.city,
                    "category": a.category,
                }
            })

        count = ingest_documents(docs)
        self.stdout.write(f'  ✓ {count} attraction documents ingested')
        return count

    # ─── FOOD ─────────────────────────────────────────────
    def _ingest_food(self):
        from food.models import FoodVendor

        self.stdout.write('🍽️ Food vendors ingesting...')
        docs = []

        for v in FoodVendor.objects.prefetch_related('menu_items').select_related('category').all():
            menu_info = ""
            for item in v.menu_items.filter(is_available=True)[:10]:
                menu_info += f"\n  - {item.name}: ₹{item.price}"

            content = f"""Food Vendor: {v.name}
Type: {v.get_vendor_type_display()}
Category: {v.category.name if v.category else 'N/A'}
Address: {v.address}
Average Cost: ₹{v.avg_cost} per person
Rating: {v.rating}/5
Verified: {'Yes' if v.is_verified else 'No'}
Description: {v.description or 'N/A'}
Popular Menu Items:{menu_info if menu_info else ' No items listed'}"""

            docs.append({
                "content": content,
                "metadata": {
                    "source": "food",
                    "title": v.name,
                    "vendor_id": str(v.id),
                    "vendor_type": v.vendor_type,
                }
            })

        count = ingest_documents(docs)
        self.stdout.write(f'  ✓ {count} food vendor documents ingested')
        return count

    # ─── RENTALS ──────────────────────────────────────────
    def _ingest_rentals(self):
        from rentals.models import Rental

        self.stdout.write('🏡 Rentals ingesting...')
        docs = []

        for r in Rental.objects.prefetch_related('amenities').all():
            amenities = ', '.join([a.name for a in r.amenities.all()]) or 'None'

            content = f"""Rental Property: {r.name}
Type: {r.get_rental_type_display()}
Address: {r.address}
Price: ₹{r.price_per_month}/month
Available Rooms: {r.available_rooms}
Verified: {'Yes' if r.is_verified else 'No'}
Amenities: {amenities}
Description: {r.description or 'N/A'}"""

            docs.append({
                "content": content,
                "metadata": {
                    "source": "rentals",
                    "title": r.name,
                    "rental_id": str(r.id),
                    "rental_type": r.rental_type,
                }
            })

        count = ingest_documents(docs)
        self.stdout.write(f'  ✓ {count} rental documents ingested')
        return count

    # ─── TRANSPORT ────────────────────────────────────────
    def _ingest_transport(self):
        from transport.models import TransportNode

        self.stdout.write('🚌 Transport nodes ingesting...')
        docs = []

        for t in TransportNode.objects.all():
            content = f"""Transport Node: {t.name}
Type: {t.get_node_type_display()}
City: {t.city}
Address: {t.address or 'N/A'}"""

            docs.append({
                "content": content,
                "metadata": {
                    "source": "transport",
                    "title": t.name,
                    "node_id": str(t.id),
                    "node_type": t.node_type,
                    "city": t.city,
                }
            })

        count = ingest_documents(docs)
        self.stdout.write(f'  ✓ {count} transport documents ingested')
        return count
