from rest_framework import serializers
from .models import Attraction


class AttractionSerializer(serializers.ModelSerializer):
    distance_km = serializers.SerializerMethodField()
    category_display = serializers.SerializerMethodField()

    class Meta:
        model = Attraction
        fields = [
            'id', 'name', 'description', 'category', 'category_display',
            'latitude', 'longitude', 'address', 'city', 'state', 'country',
            'rating', 'review_count', 'image_url', 'website', 'phone',
            'opening_hours', 'entry_fee', 'is_free', 'osm_id',
            'is_active', 'created_at', 'distance_km'
        ]

    def get_distance_km(self, obj):
        request = self.context.get('request')
        if request:
            try:
                lat = float(request.query_params.get('lat', 0))
                lon = float(request.query_params.get('lon', 0))
                if lat and lon:
                    return round(obj.distance_from(lat, lon), 1)
            except (ValueError, TypeError):
                pass
        return None

    def get_category_display(self, obj):
        icons = {
            'monument': '🏛️',
            'temple': '🛕',
            'park': '🌿',
            'museum': '🖼️',
            'nature': '🏔️',
            'other': '📍',
            'all': '🗺️',
        }
        icon = icons.get(obj.category, '📍')
        return f"{icon} {obj.get_category_display()}"


class AttractionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Attraction
        fields = [
            'id', 'name', 'category', 'latitude', 'longitude',
            'city', 'state', 'country', 'rating', 'review_count',
            'image_url', 'is_free', 'entry_fee', 'distance_km'
        ]

    def get_distance_km(self, obj):
        request = self.context.get('request')
        if request:
            try:
                lat = float(request.query_params.get('lat', 0))
                lon = float(request.query_params.get('lon', 0))
                if lat and lon:
                    return round(obj.distance_from(lat, lon), 1)
            except (ValueError, TypeError):
                pass
        return None