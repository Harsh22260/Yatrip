from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import secrets

from .models import Hotel, RoomType, RoomUnit, RatePlan, Availability, Booking
from .serializers import (
    HotelSerializer, RoomTypeSerializer, RoomUnitSerializer,
    RatePlanSerializer, AvailabilitySerializer, BookingSerializer
)


class HotelViewSet(viewsets.ModelViewSet):
    serializer_class = HotelSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Hotel.objects.all()
        # ?mine=true — sirf apne hotels
        if self.request.query_params.get('mine') == 'true':
            if self.request.user.is_authenticated:
                queryset = queryset.filter(owner=self.request.user)
            else:
                queryset = queryset.none()
        return queryset

    def perform_create(self, serializer):
        # owner automatically logged-in user set hoga
        serializer.save(owner=self.request.user)


class RoomTypeViewSet(viewsets.ModelViewSet):
    serializer_class = RoomTypeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = RoomType.objects.all()
        hotel_id = self.request.query_params.get('hotel')
        if hotel_id:
            queryset = queryset.filter(hotel_id=hotel_id)
        return queryset


class RoomUnitViewSet(viewsets.ModelViewSet):
    queryset = RoomUnit.objects.all()
    serializer_class = RoomUnitSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class RatePlanViewSet(viewsets.ModelViewSet):
    serializer_class = RatePlanSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = RatePlan.objects.all()
        room_type_id = self.request.query_params.get('room_type')
        if room_type_id:
            queryset = queryset.filter(room_type_id=room_type_id)
        return queryset


class AvailabilityViewSet(viewsets.ModelViewSet):
    serializer_class = AvailabilitySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Availability.objects.all()
        room_type_id = self.request.query_params.get('room_type')
        date_gte = self.request.query_params.get('date__gte')
        date_lte = self.request.query_params.get('date__lte')
        if room_type_id:
            queryset = queryset.filter(room_type_id=room_type_id)
        if date_gte:
            queryset = queryset.filter(date__gte=date_gte)
        if date_lte:
            queryset = queryset.filter(date__lte=date_lte)
        return queryset


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Sirf apni bookings
        return Booking.objects.filter(user=self.request.user).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        user = request.user
        data = request.data

        try:
            hotel = Hotel.objects.get(id=data.get("hotel"))
            room_type = RoomType.objects.get(id=data.get("room_type"))
        except (Hotel.DoesNotExist, RoomType.DoesNotExist):
            return Response({"error": "Invalid hotel or room_type"}, status=400)

        room_unit = None
        rate_plan = None

        if data.get("room_unit"):
            try:
                room_unit = RoomUnit.objects.get(id=data.get("room_unit"))
            except RoomUnit.DoesNotExist:
                return Response({"error": "Invalid room_unit"}, status=400)

        if data.get("rate_plan"):
            try:
                rate_plan = RatePlan.objects.get(id=data.get("rate_plan"))
            except RatePlan.DoesNotExist:
                return Response({"error": "Invalid rate_plan"}, status=400)

        try:
            check_in = date.fromisoformat(data.get("check_in"))
            check_out = date.fromisoformat(data.get("check_out"))
        except Exception:
            return Response({"error": "Invalid date format"}, status=400)

        if check_in >= check_out:
            return Response({"error": "check_out must be after check_in"}, status=400)

        nights = (check_out - check_in).days
        total_price = Decimal(room_type.base_price) * nights
        if rate_plan:
            total_price = total_price * Decimal(rate_plan.price_multiplier)

        hold_token = secrets.token_urlsafe(16)
        hold_expires = timezone.now() + timedelta(minutes=10)

        booking = Booking.objects.create(
            user=user,
            hotel=hotel,
            room_type=room_type,
            room_unit=room_unit,
            rate_plan=rate_plan,
            check_in=check_in,
            check_out=check_out,
            total_price=total_price,
            status='HELD',
            hold_token=hold_token,
            hold_expires_at=hold_expires,
            meta={"created_from": "api_hold"}
        )

        serializer = self.get_serializer(booking)
        return Response(
            {
                "message": "Booking held for 10 minutes",
                "hold_token": hold_token,
                "expires_at": hold_expires,
                "booking": serializer.data,
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        booking = self.get_object()
        token = request.data.get("hold_token")

        if booking.status != "HELD":
            return Response({"error": "Booking not in HELD state."}, status=400)
        if booking.hold_token != token:
            return Response({"error": "Invalid hold token."}, status=403)
        if booking.hold_expires_at and timezone.now() > booking.hold_expires_at:
            booking.status = "EXPIRED"
            booking.save()
            return Response({"error": "Hold expired."}, status=400)

        booking.status = "CONFIRMED"
        booking.hold_token = None
        booking.hold_expires_at = None
        booking.meta["confirmed_at"] = str(timezone.now())
        booking.save()

        return Response(
            {"message": "Booking confirmed", "booking": self.get_serializer(booking).data},
            status=200
        )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if booking.status not in ["HELD", "CONFIRMED"]:
            return Response({"error": "Only held or confirmed bookings can be cancelled."}, status=400)

        booking.status = "CANCELLED"
        booking.meta["cancelled_at"] = str(timezone.now())
        booking.save()

        return Response(
            {"message": "Booking cancelled", "booking": self.get_serializer(booking).data},
            status=200
        )