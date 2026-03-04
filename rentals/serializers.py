from rest_framework import serializers
from .models import Rental, RentalImage, RentalAmenity


class RentalImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalImage
        fields = ['id', 'image', 'uploaded_at']


class RentalAmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalAmenity
        fields = ['id', 'name']


class RentalSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    images = RentalImageSerializer(many=True, read_only=True)
    amenities = RentalAmenitySerializer(many=True, read_only=True)

    class Meta:
        model = Rental
        fields = [
            'id', 'owner_email', 'name', 'rental_type', 'description',
            'address', 'location', 'price_per_month', 'available_rooms',
            'is_verified', 'created_at', 'images', 'amenities'
        ]