from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from .models import FoodVendor, FoodImage, MenuItem, FoodCategory
from .serializers import (
    FoodVendorSerializer, FoodImageSerializer,
    MenuItemSerializer, FoodCategorySerializer
)

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user


class FoodVendorViewSet(viewsets.ModelViewSet):
    queryset = FoodVendor.objects.all().order_by('-created_at')
    serializer_class = FoodVendorSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """Find vendors near location: /api/food/nearby/?lat=28.61&lon=77.20"""
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        if not lat or not lon:
            return Response({"error": "Latitude and longitude required."}, status=400)
        user_location = Point(float(lon), float(lat), srid=4326)
        vendors = FoodVendor.objects.annotate(distance=Distance('location', user_location)).order_by('distance')[:15]
        serializer = self.get_serializer(vendors, many=True)
        return Response(serializer.data)


class FoodImageViewSet(viewsets.ModelViewSet):
    queryset = FoodImage.objects.all()
    serializer_class = FoodImageSerializer
    permission_classes = [permissions.IsAuthenticated]


class MenuItemViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class FoodCategoryViewSet(viewsets.ModelViewSet):
    queryset = FoodCategory.objects.all()
    serializer_class = FoodCategorySerializer
    permission_classes = [permissions.IsAdminUser]