"""
Management Command: ingest_data
"""

from django.core.management.base import BaseCommand
from chatbot.rag_engine import ingest_text, ingest_url, clear_vectorstore


YATRIP_BASE_KNOWLEDGE = [
    {
        "title": "About Yatrip",
        "content": """
Yatrip is an Indian travel platform that makes travel planning easy and affordable.
We offer the following services:
- Hotel Bookings: Budget to luxury hotels across India
- Food & Restaurants: Discover local cuisine and restaurants at your destination
- Attractions: Top tourist spots, monuments, and hidden gems
- Transport: Bus, cab, auto rentals and inter-city travel options
- Rentals: Bike, scooter, and car rentals for local commute
- Reviews: Authentic user reviews for all listed services
Yatrip focuses on making travel within India seamless.
        """,
    },
    {
        "title": "Yatrip Hotel Booking",
        "content": """
Yatrip offers hotel bookings across India with:
- Budget guesthouses, mid-range hotels, and luxury resorts
- Verified photos and authentic reviews
- Instant booking confirmation
- Free cancellation options on many properties
- Special deals for early bookings
Users can filter by price, rating, amenities, and location.
        """,
    },
    {
        "title": "Yatrip Food & Restaurants",
        "content": """
Yatrip food section helps travelers discover:
- Local dhabas with authentic regional cuisine
- Popular restaurants and cafes
- Street food spots loved by locals
- Vegetarian and vegan-friendly options
- Fine dining experiences
        """,
    },
    {
        "title": "Yatrip Attractions",
        "content": """
Yatrip lists top travel attractions across India including:
- Historical monuments and UNESCO sites
- Natural wonders: mountains, beaches, waterfalls
- Religious and spiritual destinations
- Adventure activities: trekking, rafting, paragliding
- Family-friendly spots and theme parks
        """,
    },
    {
        "title": "Yatrip Transport & Rentals",
        "content": """
Yatrip transport section covers:
- Inter-city buses and cabs
- Airport transfers
- Local auto/cab/rickshaw options
- Bike and scooter rentals for self-exploration
- Car rentals with and without drivers
        """,
    },
    {
        "title": "Yatrip Reviews System",
        "content": """
Yatrip has a trusted review system where:
- Only verified travelers can leave reviews
- Hotels, restaurants, and attractions all have ratings
- Photos can be uploaded with reviews
        """,
    },
]


class Command(BaseCommand):
    help = "Ingest data into ChromaDB for RAG chatbot"

    def add_arguments(self, parser):
        parser.add_argument("--url", type=str, help="Ingest content from a specific URL")
        parser.add_argument("--clear", action="store_true", help="Clear all ChromaDB data")
        parser.add_argument("--base_only", action="store_true", help="Only ingest base Yatrip knowledge")

    def handle(self, *args, **options):

        if options["clear"]:
            self.stdout.write("Clearing ChromaDB...")
            clear_vectorstore()
            self.stdout.write(self.style.SUCCESS("ChromaDB cleared!"))
            return

        if options.get("url"):
            url = options["url"]
            self.stdout.write(f"Ingesting URL: {url}")
            count = ingest_url(url)
            self.stdout.write(self.style.SUCCESS(f"Ingested {count} chunks from URL"))
            return

        self.stdout.write("Ingesting Yatrip base knowledge...")
        total = 0
        for doc in YATRIP_BASE_KNOWLEDGE:
            count = ingest_text(
                title=doc["title"],
                content=doc["content"],
                source="website",
            )
            total += count
            self.stdout.write(f"  Done: {doc['title']} -> {count} chunks")

        if options.get("base_only"):
            self.stdout.write(self.style.SUCCESS(f"Done! Total chunks: {total}"))
            return

        self.stdout.write("Ingesting data from database...")

        try:
            from hotels.models import Hotel
            hotels = Hotel.objects.all()[:50]
            for hotel in hotels:
                content = f"Hotel: {hotel.name}\nDescription: {getattr(hotel, 'description', '')}"
                ingest_text(f"Hotel: {hotel.name}", content, source="database")
            self.stdout.write(f"  Hotels: {hotels.count()} ingested")
        except Exception as e:
            self.stdout.write(f"  Hotels skipped: {e}")

        try:
            from attractions.models import Attraction
            attractions = Attraction.objects.all()[:50]
            for attr in attractions:
                content = f"Attraction: {attr.name}\nDescription: {getattr(attr, 'description', '')}"
                ingest_text(f"Attraction: {attr.name}", content, source="database")
            self.stdout.write(f"  Attractions: {attractions.count()} ingested")
        except Exception as e:
            self.stdout.write(f"  Attractions skipped: {e}")

        try:
            from food.models import Restaurant
            restaurants = Restaurant.objects.all()[:50]
            for rest in restaurants:
                content = f"Restaurant: {rest.name}\nDescription: {getattr(rest, 'description', '')}"
                ingest_text(f"Restaurant: {rest.name}", content, source="database")
            self.stdout.write(f"  Restaurants: {restaurants.count()} ingested")
        except Exception as e:
            self.stdout.write(f"  Restaurants skipped: {e}")

        self.stdout.write(self.style.SUCCESS(f"All done! Total chunks: {total}"))
