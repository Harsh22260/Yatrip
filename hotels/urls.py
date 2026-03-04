# hotels/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    HotelViewSet,
    RoomTypeViewSet,
    RatePlanViewSet,
    AvailabilityViewSet,
    BookingViewSet,
)

router = DefaultRouter()
router.register(r'hotels', HotelViewSet, basename='hotel')
router.register(r'room-types', RoomTypeViewSet, basename='roomtype')
router.register(r'rate-plans', RatePlanViewSet, basename='rateplan')
router.register(r'availability', AvailabilityViewSet, basename='availability')
router.register(r'bookings', BookingViewSet, basename='booking')

urlpatterns = [
    path('', include(router.urls)),
]