from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from .models import TransportNode
from .serializers import TransportNodeSerializer

class TransportNodeViewSet(viewsets.ModelViewSet):
    queryset = TransportNode.objects.all().order_by('-created_at')
    serializer_class = TransportNodeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        if not lat or not lon:
            return Response({"error": "Latitude and longitude required"}, status=400)
        user_location = Point(float(lon), float(lat), srid=4326)
        nodes = TransportNode.objects.annotate(distance=Distance('location', user_location)).order_by('distance')[:20]
        serializer = self.get_serializer(nodes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def route(self, request):
        """Start + End coordinate → return route via OpenRouteService"""
        start_lat = request.query_params.get('start_lat')
        start_lon = request.query_params.get('start_lon')
        end_lat = request.query_params.get('end_lat')
        end_lon = request.query_params.get('end_lon')

        if not all([start_lat, start_lon, end_lat, end_lon]):
            return Response({"error": "All coordinates required"}, status=400)

        # Example placeholder (later integrate OpenRouteService)
        return Response({
            "start": [float(start_lat), float(start_lon)],
            "end": [float(end_lat), float(end_lon)],
            "distance_km": 5.6,
            "duration_min": 12,
            "status": "mocked (replace with real route API)"
        })