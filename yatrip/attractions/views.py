from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from .models import Attraction
from .serializers import AttractionSerializer

class AttractionViewSet(viewsets.ModelViewSet):
    queryset = Attraction.objects.all().order_by('-created_at')
    serializer_class = AttractionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        if not lat or not lon:
            return Response({"error": "Latitude and longitude required"}, status=400)
        user_location = Point(float(lon), float(lat), srid=4326)
        attractions = Attraction.objects.annotate(distance=Distance('location', user_location)).order_by('distance')[:15]
        serializer = self.get_serializer(attractions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def city(self, request):
        """Filter attractions by city: /api/attractions/city/?name=Agra"""
        city = request.query_params.get('name')
        if not city:
            return Response({"error": "City name required"}, status=400)
        attractions = Attraction.objects.filter(city__icontains=city)
        serializer = self.get_serializer(attractions, many=True)
        return Response(serializer.data)