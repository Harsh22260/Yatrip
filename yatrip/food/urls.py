## ── food/urls.py ─────────────────────────────────────────────────────────────
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FoodPlaceViewSet

router = DefaultRouter()
router.register(r'food', FoodPlaceViewSet, basename='food')

urlpatterns = [path('', include(router.urls))]

# GET /api/food/                        → list (all filters)
# GET /api/food/{id}/                   → detail
# GET /api/food/nearby/?lat=&lon=       → nearby 10km
# GET /api/food/categories/             → category list
# GET /api/food/cuisines/               → cuisine list
# GET /api/food/random/                 → random places