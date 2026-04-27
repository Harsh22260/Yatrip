from rest_framework.routers import DefaultRouter
from .views import AttractionViewSet

router = DefaultRouter()
router.register(r'', AttractionViewSet, basename='attraction')

urlpatterns = router.urls