from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AttractionViewSet

router = DefaultRouter()
router.register(r'attractions', AttractionViewSet, basename='attraction')

urlpatterns = [
    path('', include(router.urls)),
]

# Generated URLs:
# GET  /api/attractions/                         → list (with all filters)
# GET  /api/attractions/{id}/                    → detail
# GET  /api/attractions/nearby/?lat=&lon=        → nearby 400km
# GET  /api/attractions/categories/              → all categories with counts
# GET  /api/attractions/random/                  → random attractions