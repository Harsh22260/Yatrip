from rest_framework import serializers
from .models import Hotel, HotelImage, Room, Amenity, HotelPolicy

class HotelImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelImage
        fields = ['id', 'image', 'uploaded_at']


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'room_type', 'capacity', 'price', 'is_available']


class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ['id', 'name']


class HotelPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelPolicy
        fields = ['check_in', 'check_out', 'cancellation_policy', 'extra_guest_charge']


class HotelSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    images = HotelImageSerializer(many=True, read_only=True)
    rooms = RoomSerializer(many=True, read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True)
    policy = HotelPolicySerializer(read_only=True)

    class Meta:
        model = Hotel
        fields = [
            'id', 'owner_email', 'name', 'description', 'address',
            'location', 'price_per_night', 'rating', 'is_verified',
            'created_at', 'images', 'rooms', 'amenities', 'policy'
        ]