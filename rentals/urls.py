from rest_framework.routers import DefaultRouter
from .views import RentalViewSet, RentalImageViewSet, RentalAmenityViewSet

router = DefaultRouter()
router.register(r'', RentalViewSet, basename='rental')
router.register(r'images', RentalImageViewSet, basename='rental-image')
router.register(r'amenities', RentalAmenityViewSet, basename='rental-amenity')

urlpatterns = router.urls