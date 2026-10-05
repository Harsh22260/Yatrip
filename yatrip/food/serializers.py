from rest_framework import serializers
from .models import FoodPlace, MenuItem


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model  = MenuItem
        fields = [
            'id', 'name', 'description', 'price', 'image_url',
            'is_veg', 'is_available', 'created_at',
        ]
        read_only_fields = ['created_at']

    # image is what MenuItemCard reads; image_url is the model field name. Sending
    # both means the card works without a frontend rename.
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['image'] = instance.image_url
        return data


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
            'is_verified',
        ]

    def get_distance_km(self, obj):
        # The view already computed this while filtering and sorting, so reuse it
        # rather than recomputing haversine once per row during serialisation.
        cached = getattr(obj, '_distance_km', None)
        if cached is not None:
            return round(cached, 1)

        req = self.context.get('request')
        if req:
            try:
                lat = float(req.query_params.get('lat', 0))
                lon = float(req.query_params.get('lon', 0))
                if lat or lon:
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
        return '₹' * (obj.price_level or 0)


class FoodPlaceDetailSerializer(FoodPlaceListSerializer):
    image_credit = serializers.CharField(read_only=True, allow_null=True)
    menu_items = MenuItemSerializer(many=True, read_only=True)
    category_name = serializers.SerializerMethodField()

    class Meta(FoodPlaceListSerializer.Meta):
        fields = FoodPlaceListSerializer.Meta.fields + [
            'description', 'address', 'country', 'website', 'phone',
            'opening_hours', 'avg_cost_for_two', 'outdoor_seating',
            'osm_id', 'image_credit', 'created_at', 'category_name',
            'menu_items',
        ]

    def get_category_name(self, obj):
        return obj.get_category_display()


class FoodPlaceWriteSerializer(serializers.ModelSerializer):
    """
    Owner-facing payload. ``owner``, ``is_verified`` and ``osm_id`` are excluded
    from the writable surface: the first two are set by the server, and letting a
    client claim an OSM row would let anyone take over someone else's import.
    """

    class Meta:
        model  = FoodPlace
        fields = [
            'id', 'name', 'description', 'category', 'cuisine',
            'latitude', 'longitude', 'address', 'city', 'state', 'country',
            'price_level', 'avg_cost_for_two', 'image_url', 'website', 'phone',
            'opening_hours', 'is_veg', 'home_delivery', 'takeaway',
            'outdoor_seating',
        ]
        read_only_fields = ['id']

    def validate_latitude(self, value):
        if not -90 <= float(value) <= 90:
            raise serializers.ValidationError('Latitude must be between -90 and 90.')
        return value

    def validate_longitude(self, value):
        if not -180 <= float(value) <= 180:
            raise serializers.ValidationError('Longitude must be between -180 and 180.')
        return value