from rest_framework import serializers

from .models import Availability, Booking, Hotel, RatePlan, RoomType, RoomUnit


# 🏨 HOTEL
class HotelSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    room_type_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Hotel
        fields = [
            "id",
            "owner",
            "owner_username",
            "name",
            "description",
            "address",
            "location",
            "rating",
            "is_verified",
            "room_type_count",
            "created_at",
        ]
        # owner/owner_username/room_type_count were writable, so a client could
        # set is_verified on itself or reassign a hotel to another account.
        read_only_fields = ["owner", "owner_username", "room_type_count", "is_verified"]


# 🏠 ROOM TYPES & UNITS
class RoomUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomUnit
        fields = ["id", "unit_code", "is_available", "room_type"]


class RoomTypeSerializer(serializers.ModelSerializer):
    units = RoomUnitSerializer(many=True, read_only=True)
    hotel_name = serializers.CharField(source="hotel.name", read_only=True)
    available_units = serializers.IntegerField(read_only=True)

    class Meta:
        model = RoomType
        fields = [
            "id",
            "hotel",
            "hotel_name",
            "name",
            "description",
            "capacity",
            "base_price",
            "total_units",
            "available_units",
            "units",
            "created_at",
        ]


# 💰 RATE PLAN
class RatePlanSerializer(serializers.ModelSerializer):
    final_price = serializers.SerializerMethodField()

    class Meta:
        model = RatePlan
        fields = [
            "id",
            "room_type",
            "name",
            "price_multiplier",
            "refundable",
            # breakfast_included and discount_percent were on the model but were
            # never serialised, so the frontend could not show or apply them.
            "breakfast_included",
            "discount_percent",
            "min_stay",
            "final_price",
        ]

    def get_final_price(self, obj) -> str:
        return f"{obj.get_final_price():.2f}"

    def validate_price_multiplier(self, value):
        if value <= 0:
            raise serializers.ValidationError("price_multiplier must be greater than 0.")
        return value

    def validate_discount_percent(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError("discount_percent must be between 0 and 100.")
        return value


# 📅 AVAILABILITY
class AvailabilitySerializer(serializers.ModelSerializer):
    # available_units is the whole point of this endpoint; it was missing, so the
    # frontend always saw the row without knowing how many rooms were left.
    available_units = serializers.IntegerField(read_only=True)

    class Meta:
        model = Availability
        fields = [
            "id",
            "room_unit",
            "room_type",
            "date",
            "available_units",
            "is_booked",
            "price",
            "updated_at",
        ]


# 📘 BOOKING
class BookingSerializer(serializers.ModelSerializer):
    hotel_name = serializers.CharField(source="hotel.name", read_only=True)
    room_type_name = serializers.CharField(source="room_type.name", read_only=True)
    nights = serializers.IntegerField(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "user",
            "hotel",
            "hotel_name",
            "room_unit",
            "room_type",
            "room_type_name",
            "rate_plan",
            "check_in",
            "check_out",
            "nights",
            "total_price",
            "status",
            "hold_token",
            "hold_expires_at",
            "created_at",
            "meta",
        ]
        # total_price/hotel/dates are derived on the server; exposing them for
        # write let a client rewrite the price of an existing booking.
        read_only_fields = [
            "id",
            "user",
            "hotel",
            "room_unit",
            "room_type",
            "rate_plan",
            "check_in",
            "check_out",
            "total_price",
            "status",
            "hold_token",
            "hold_expires_at",
            "created_at",
        ]
