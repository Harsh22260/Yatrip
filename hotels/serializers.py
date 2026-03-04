from rest_framework import serializers
from .models import Hotel, RoomType, RoomUnit, RatePlan, Availability, Booking


# 🏨 HOTEL
class HotelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hotel
        fields = [
            'id',
            'owner',
            'name',
            'description',
            'address',
            'location',
            'rating',
            'is_verified',
            'created_at'
        ]


# 🏠 ROOM TYPES & UNITS
class RoomUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomUnit
        fields = ['id', 'unit_code', 'is_available', 'room_type']


class RoomTypeSerializer(serializers.ModelSerializer):
    units = RoomUnitSerializer(many=True, read_only=True)

    class Meta:
        model = RoomType
        fields = [
            'id', 'hotel', 'name', 'description', 'capacity',
            'base_price', 'units'
        ]


# 💰 RATE PLAN
class RatePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatePlan
        fields = [
            'id', 'room_type', 'name', 'price_multiplier',
            'refundable', 'min_stay'
        ]


# 📅 AVAILABILITY
class AvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Availability
        fields = [
            'id', 'room_unit', 'room_type',
            'date', 'is_booked', 'price'
        ]


# 📘 BOOKING
class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            'id', 'user', 'hotel', 'room_unit', 'room_type', 'rate_plan',
            'check_in', 'check_out', 'total_price', 'status',
            'hold_token', 'hold_expires_at', 'created_at', 'meta'
        ]
        read_only_fields = [
            'id', 'status', 'hold_token', 'hold_expires_at', 'created_at'
        ]