from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from .models import Rental, RentalImage, RentalAmenity
from .serializers import RentalSerializer, RentalImageSerializer, RentalAmenitySerializer


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user


class RentalViewSet(viewsets.ModelViewSet):
    queryset = Rental.objects.all().order_by('-created_at')
    serializer_class = RentalSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        if not lat or not lon:
            return Response({"error": "Latitude and longitude required."}, status=400)
        user_location = Point(float(lon), float(lat), srid=4326)
        rentals = Rental.objects.annotate(distance=Distance('location', user_location)).order_by('distance')[:10]
        serializer = self.get_serializer(rentals, many=True)
        return Response(serializer.data)


class RentalImageViewSet(viewsets.ModelViewSet):
    queryset = RentalImage.objects.all()
    serializer_class = RentalImageSerializer
    permission_classes = [permissions.IsAuthenticated]


class RentalAmenityViewSet(viewsets.ModelViewSet):
    queryset = RentalAmenity.objects.all()
    serializer_class = RentalAmenitySerializer
    permission_classes = [permissions.IsAdminUser]