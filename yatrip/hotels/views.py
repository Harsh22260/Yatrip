from __future__ import annotations

from datetime import date

from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response

from . import services
from .models import Availability, Booking, Hotel, RatePlan, RoomType, RoomUnit
from .serializers import (
    AvailabilitySerializer,
    BookingSerializer,
    HotelSerializer,
    RatePlanSerializer,
    RoomTypeSerializer,
    RoomUnitSerializer,
)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Read for anyone, write only for the hotel's owner.

    The previous viewsets used ``IsAuthenticatedOrReadOnly``, which meant *any*
    logged-in user could edit or delete another hotel's rooms, prices and
    availability calendar.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return getattr(obj, "owner_id", None) == getattr(request.user, "id", None)


def _owns_hotel(request, hotel_id) -> bool:
    return Hotel.objects.filter(id=hotel_id, owner=request.user).exists()


class HotelOwnedChildViewSet(viewsets.ModelViewSet):
    """
    Base for viewsets whose rows hang off a hotel.

    Write access is resolved through ``?hotel=`` or the object's own relation,
    so a user cannot touch a child object that belongs to someone else.
    """

    permission_classes = [IsOwnerOrReadOnly]

    #: URL query param naming the parent hotel.
    parent_param = "hotel"

    def _parent_hotel_id(self):
        request = self.request
        value = request.query_params.get(self.parent_param)
        if value:
            return value
        if self.kwargs.get("pk"):
            obj = self.get_object() if self.request.method != "POST" else None
            if obj is not None:
                return getattr(obj, "hotel_id", None) or getattr(
                    getattr(obj, "room_type", None), "hotel_id", None
                )
        if request.data:
            return request.data.get(self.parent_param) or request.data.get("hotel")
        return None

    def _hotel_id_from_request(self):
        """
        Resolve the parent hotel for a write.

        ``parent_param`` names the immediate parent, which is not always a
        hotel: for rate plans it is ``room_type``. Passing a RoomType UUID
        straight into ``Hotel.objects.filter(id=...)`` returned a 403 for every
        legitimate owner, so the parent chain is walked properly here.
        """
        request = self.request
        value = request.data.get(self.parent_param) or request.data.get("hotel")
        if not value:
            return None
        if self.parent_param == "room_type":
            return RoomType.objects.filter(id=value).values_list("hotel_id", flat=True).first()
        return value

    def create(self, request, *args, **kwargs):
        hotel_id = self._hotel_id_from_request()
        if not hotel_id:
            return Response(
                {"error": f"{self.parent_param} is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not _owns_hotel(request, hotel_id):
            return Response(
                {"error": "You do not own this hotel."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)

    def perform_update(self, serializer):
        obj = self.get_object()
        hotel_id = getattr(obj, "hotel_id", None) or getattr(
            getattr(obj, "room_type", None), "hotel_id", None
        )
        if not _owns_hotel(self.request, hotel_id):
            raise permissions.PermissionDenied("You do not own this hotel.")
        serializer.save()

    def perform_destroy(self, instance):
        hotel_id = getattr(instance, "hotel_id", None) or getattr(
            getattr(instance, "room_type", None), "hotel_id", None
        )
        if not _owns_hotel(self.request, hotel_id):
            raise permissions.PermissionDenied("You do not own this hotel.")
        instance.delete()


class HotelViewSet(viewsets.ModelViewSet):
    serializer_class = HotelSerializer
    permission_classes = [IsOwnerOrReadOnly]
    filterset_fields = ["owner", "is_verified"]

    def get_queryset(self):
        queryset = Hotel.objects.all()
        # ?mine=true — sirf apne hotels
        if self.request.query_params.get("mine") == "true":
            if self.request.user.is_authenticated:
                queryset = queryset.filter(owner=self.request.user)
            else:
                queryset = queryset.none()
        return queryset

    def perform_create(self, serializer):
        # owner is always the logged-in user, never whatever the client sent.
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post"])
    def generate_availability(self, request, pk=None):
        """Re-create the rolling availability calendar for this hotel."""
        hotel = self.get_object()
        if hotel.owner_id != request.user.id:
            return Response({"error": "You do not own this hotel."}, status=status.HTTP_403_FORBIDDEN)
        hotel.generate_availability()
        return Response({"message": "Availability generated.", "hotel": hotel.id})


class RoomTypeViewSet(HotelOwnedChildViewSet):
    serializer_class = RoomTypeSerializer

    def get_queryset(self):
        queryset = RoomType.objects.select_related("hotel").prefetch_related("units")
        hotel_id = self.request.query_params.get("hotel")
        if hotel_id:
            queryset = queryset.filter(hotel_id=hotel_id)
        return queryset


class RoomUnitViewSet(HotelOwnedChildViewSet):
    serializer_class = RoomUnitSerializer
    parent_param = "room_type"

    def get_queryset(self):
        queryset = RoomUnit.objects.select_related("room_type__hotel")
        room_type_id = self.request.query_params.get("room_type")
        if room_type_id:
            queryset = queryset.filter(room_type_id=room_type_id)
        hotel_id = self.request.query_params.get("hotel")
        if hotel_id:
            queryset = queryset.filter(room_type__hotel_id=hotel_id)
        return queryset


class RatePlanViewSet(HotelOwnedChildViewSet):
    serializer_class = RatePlanSerializer
    parent_param = "room_type"

    def get_queryset(self):
        queryset = RatePlan.objects.select_related("room_type__hotel")
        room_type_id = self.request.query_params.get("room_type")
        if room_type_id:
            queryset = queryset.filter(room_type_id=room_type_id)
        hotel_id = self.request.query_params.get("hotel")
        if hotel_id:
            queryset = queryset.filter(room_type__hotel_id=hotel_id)
        return queryset


class AvailabilityViewSet(HotelOwnedChildViewSet):
    serializer_class = AvailabilitySerializer
    parent_param = "room_type"

    def get_queryset(self):
        queryset = Availability.objects.select_related("room_type__hotel")
        room_type_id = self.request.query_params.get("room_type")
        date_gte = self.request.query_params.get("date__gte")
        date_lte = self.request.query_params.get("date__lte")
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
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).select_related(
            "hotel", "room_type", "rate_plan"
        ).order_by("-created_at")

    def _resolve(self, data, key, model, label):
        value = data.get(key)
        if not value:
            return None
        try:
            return model.objects.get(id=value)
        except model.DoesNotExist:
            raise services.BookingError(f"Invalid {label}", code=f"invalid_{label}")

    @staticmethod
    def _parse_date(raw, label):
        try:
            return date.fromisoformat(raw)
        except (TypeError, ValueError):
            raise services.BookingError(f"Invalid {label} date format", code="bad_dates")

    def create(self, request, *args, **kwargs):
        data = request.data

        try:
            room_type = RoomType.objects.select_related("hotel").get(id=data.get("room_type"))
            check_in = self._parse_date(data.get("check_in"), "check_in")
            check_out = self._parse_date(data.get("check_out"), "check_out")
            rate_plan = self._resolve(data, "rate_plan", RatePlan, "rate_plan")
            room_unit = self._resolve(data, "room_unit", RoomUnit, "room_unit")

            if not data.get("hotel"):
                hotel_id = room_type.hotel_id
            else:
                hotel_id = data.get("hotel")
                if str(hotel_id) != str(room_type.hotel_id):
                    raise services.BookingError(
                        "That room type does not belong to the selected hotel.",
                        code="hotel_mismatch",
                    )

            try:
                units = int(data.get("units", 1))
            except (TypeError, ValueError):
                raise services.BookingError("units must be a whole number", code="bad_units")

            booking = services.hold_rooms(
                user=request.user,
                room_type=room_type,
                check_in=check_in,
                check_out=check_out,
                rate_plan=rate_plan,
                room_unit=room_unit,
                units=units,
                meta={"created_from": "api_hold"},
            )
        except services.BookingError as exc:
            return Response({"error": exc.message, "code": exc.code}, status=exc.status)

        return Response(
            {
                "message": f"Booking held for {services.HOLD_MINUTES} minutes",
                "hold_token": booking.hold_token,
                "expires_at": booking.hold_expires_at,
                "booking": self.get_serializer(booking).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        booking = self.get_object()
        try:
            services.confirm_booking(booking, request.data.get("hold_token", ""))
        except services.BookingError as exc:
            return Response({"error": exc.message, "code": exc.code}, status=exc.status)
        return Response(
            {"message": "Booking confirmed", "booking": self.get_serializer(booking).data}
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if booking.status not in ("HELD", "CONFIRMED"):
            return Response(
                {"error": "Only held or confirmed bookings can be cancelled.", "code": "bad_state"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        services.release_rooms(booking, reason="user_cancelled")
        return Response(
            {"message": "Booking cancelled", "booking": self.get_serializer(booking).data}
        )

    @action(detail=False, methods=["get"], url_path="availability")
    def availability(self, request):
        """
        Pre-flight availability check for a stay.

        Read-only and advisory: the authoritative, race-free check happens when
        the hold is created.
        """
        try:
            room_type = RoomType.objects.get(id=request.query_params.get("room_type"))
            check_in = self._parse_date(request.query_params.get("check_in"), "check_in")
            check_out = self._parse_date(request.query_params.get("check_out"), "check_out")
            try:
                units = int(request.query_params.get("units", 1))
            except (TypeError, ValueError):
                raise services.BookingError("units must be a whole number", code="bad_units")
        except RoomType.DoesNotExist:
            return Response({"error": "Invalid room_type", "code": "invalid_room_type"}, status=400)
        except services.BookingError as exc:
            return Response({"error": exc.message, "code": exc.code}, status=exc.status)

        available = Booking.is_available(room_type, check_in, check_out, units=units)
        return Response(
            {
                "room_type": room_type.id,
                "check_in": check_in,
                "check_out": check_out,
                "nights": max((check_out - check_in).days, 0),
                "units": units,
                "available": available,
                "from_price": room_type.base_price,
            }
        )

    def perform_update(self, serializer):
        """
        Only ``meta`` may be edited on an active booking.

        ``serializer.validated_data`` cannot be used for this check: DRF strips
        read-only fields out of it, so a PATCH carrying ``total_price`` arrives
        looking empty and the guard silently passed. The raw request body is
        inspected instead.
        """
        booking = self.get_object()
        if booking.status in ("HELD", "CONFIRMED"):
            immutable = {
                "total_price",
                "check_in",
                "check_out",
                "hotel",
                "room_type",
                "room_unit",
                "rate_plan",
                "user",
                "status",
            }
            submitted = {key for key in self.request.data if key in immutable}
            if submitted:
                # DRF only converts its own ValidationError subclasses into a
                # 400 response, so raising BookingError here would have become
                # an uncaught 500.
                raise DRFValidationError(
                    {
                        "detail": (
                            "Cannot change "
                            + ", ".join(sorted(submitted))
                            + " on an active booking. Cancel it and book again."
                        ),
                        "code": "immutable_field",
                    }
                )
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        booking = self.get_object()
        if booking.status in ("HELD", "CONFIRMED"):
            services.release_rooms(booking, reason="user_deleted")
        return super().destroy(request, *args, **kwargs)
