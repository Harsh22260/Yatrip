from rest_framework.routers import DefaultRouter
from .views import (
    FoodVendorViewSet, FoodImageViewSet,
    MenuItemViewSet, FoodCategoryViewSet
)

router = DefaultRouter()
router.register(r'', FoodVendorViewSet, basename='food-vendor')
router.register(r'images', FoodImageViewSet, basename='food-image')
router.register(r'menu', MenuItemViewSet, basename='menu-item')
router.register(r'categories', FoodCategoryViewSet, basename='food-category')

urlpatterns = router.urls