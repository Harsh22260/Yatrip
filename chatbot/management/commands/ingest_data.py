from django.core.management.base import BaseCommand
from sentence_transformers import SentenceTransformer
from chatbot.models import KnowledgeDocument
from hotels.models import Hotel
from food.models import FoodVendor
from attractions.models import Attraction
from rentals.models import Rental

class Command(BaseCommand):
    help = "Ingests Hotels, Rentals, Food, Attractions into Knowledge Base"

    def handle(self, *args, **kwargs):
        model = SentenceTransformer('all-MiniLM-L6-v2')

        # 🔹 Hotels
        for h in Hotel.objects.all():
            text = f"{h.name}. {h.description}. Address: {h.address}"
            emb = model.encode(text).tolist()
            KnowledgeDocument.objects.create(
                source_type="hotel",
                title=h.name,
                content=text,
                embedding=emb,
                metadata={"id": h.id, "price": str(h.price_per_night)}
            )
        self.stdout.write(self.style.SUCCESS("✅ Hotels added"))

        # 🔹 Rentals
        for r in Rental.objects.all():
            text = f"{r.name}. {r.description}. Address: {r.address}"
            emb = model.encode(text).tolist()
            KnowledgeDocument.objects.create(
                source_type="rental",
                title=r.name,
                content=text,
                embedding=emb,
                metadata={"id": r.id, "type": r.rental_type}
            )
        self.stdout.write(self.style.SUCCESS("✅ Rentals added"))

        # 🔹 Food
        for f in FoodVendor.objects.all():
            text = f"{f.name}. {f.description}. Address: {f.address}"
            emb = model.encode(text).tolist()
            KnowledgeDocument.objects.create(
                source_type="food",
                title=f.name,
                content=text,
                embedding=emb,
                metadata={"id": f.id, "avg_cost": str(f.avg_cost)}
            )
        self.stdout.write(self.style.SUCCESS("✅ Food vendors added"))

        # 🔹 Attractions
        for a in Attraction.objects.all():
            text = f"{a.name}. {a.description}. City: {a.city}. Address: {a.address}"
            emb = model.encode(text).tolist()
            KnowledgeDocument.objects.create(
                source_type="attraction",
                title=a.name,
                content=text,
                embedding=emb,
                metadata={"id": a.id, "city": a.city}
            )
        self.stdout.write(self.style.SUCCESS("✅ Attractions added"))