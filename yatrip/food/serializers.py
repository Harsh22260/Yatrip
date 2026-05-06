from rest_framework import serializers
from .models import FoodPlace


class FoodPlaceListSerializer(serializers.ModelSerializer):
    distance_km     = serializers.SerializerMethodField()
    category_display = serializers.SerializerMethodField()
    price_display   = serializers.SerializerMethodField()

    class Meta:
        model  = FoodPlace
        fields = [
            'id', 'name', 'category', 'category_display', 'cuisine',
            'latitude', 'longitude', 'city', 'state',
            'rating', 'review_count', 'price_level', 'price_display',
            'image_url', 'is_veg', 'is_open_now',
            'home_delivery', 'takeaway', 'distance_km',
        ]

    def get_distance_km(self, obj):
        req = self.context.get('request')
        if req:
            try:
                lat = float(req.query_params.get('lat', 0))
                lon = float(req.query_params.get('lon', 0))
                if lat and lon:
                    return round(obj.distance_from(lat, lon), 1)
            except (ValueError, TypeError):
                pass
        return None

    def get_category_display(self, obj):
        icons = {
            'street_food': '🥘', 'restaurant': '🍽️', 'cafe': '☕',
            'dhaba': '🍛', 'bakery': '🥐', 'sweet_shop': '🍬',
            'juice_bar': '🥤', 'fast_food': '🍔', 'other': '🍴',
        }
        return f"{icons.get(obj.category,'🍴')} {obj.get_category_display()}"

    def get_price_display(self, obj):
        return '₹' * obj.price_level


class FoodPlaceDetailSerializer(FoodPlaceListSerializer):
    class Meta(FoodPlaceListSerializer.Meta):
        fields = FoodPlaceListSerializer.Meta.fields + [
            'description', 'address', 'country', 'website', 'phone',
            'opening_hours', 'avg_cost_for_two', 'outdoor_seating',
            'osm_id', 'created_at',
        ]