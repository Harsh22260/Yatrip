# hotels/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AvailabilityViewSet,
    BookingViewSet,
    HotelViewSet,
    RatePlanViewSet,
    RoomTypeViewSet,
    RoomUnitViewSet,
)

router = DefaultRouter()
router.register(r'hotels', HotelViewSet, basename='hotel')
router.register(r'room-types', RoomTypeViewSet, basename='roomtype')
# RoomUnitViewSet existed but was never registered, so /room-units/ 404'd even
# though the frontend links to it.
router.register(r'room-units', RoomUnitViewSet, basename='roomunit')
router.register(r'rate-plans', RatePlanViewSet, basename='rateplan')
router.register(r'availability', AvailabilityViewSet, basename='availability')
router.register(r'bookings', BookingViewSet, basename='booking')

urlpatterns = [
    path('', include(router.urls)),
]