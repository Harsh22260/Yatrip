from rest_framework.routers import DefaultRouter
from .views import (
    HotelViewSet, HotelImageViewSet, RoomViewSet,
    AmenityViewSet, HotelPolicyViewSet
)

router = DefaultRouter()
router.register(r'', HotelViewSet, basename='hotel')
router.register(r'images', HotelImageViewSet, basename='hotel-image')
router.register(r'rooms', RoomViewSet, basename='room')
router.register(r'amenities', AmenityViewSet, basename='amenity')
router.register(r'policies', HotelPolicyViewSet, basename='policy')

urlpatterns = router.urls