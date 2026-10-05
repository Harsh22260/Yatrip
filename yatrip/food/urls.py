## ── food/urls.py ─────────────────────────────────────────────────────────────
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FoodPlaceViewSet

router = DefaultRouter()
router.register(r'food', FoodPlaceViewSet, basename='food')

urlpatterns = [path('', include(router.urls))]

# Public reads
# GET  /api/food/                        → list (all filters, ?mine=true for own)
# GET  /api/food/{id}/                   → detail (includes menu_items)
# GET  /api/food/nearby/?lat=&lon=       → nearby, db-only, reports `sparse`
# GET  /api/food/categories/             → category list with counts
# GET  /api/food/cuisines/               → cuisine list
# GET  /api/food/random/                 → random places
#
# Business writes (auth required, owner-scoped)
# POST   /api/food/                      → register an outlet
# PATCH  /api/food/{id}/                 → edit own outlet
# GET    /api/food/{id}/menu-items/      → the menu
# POST   /api/food/{id}/menu-items/      → add a dish
# DELETE /api/food/{id}/menu-items/{i}/  → remove a dish
#
# OSM import. Deliberately explicit and rate limited: these are the only routes
# that hit Overpass, and they must never run inside a browse request.
# POST /api/food/import-area/   { lat, lon, radius }
# GET  /api/food/import-city/?q=Kushinagar   → works for villages too