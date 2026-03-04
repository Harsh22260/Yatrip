from rest_framework.routers import DefaultRouter
from .views import TransportNodeViewSet

router = DefaultRouter()
router.register(r'', TransportNodeViewSet, basename='transport-node')

urlpatterns = router.urls