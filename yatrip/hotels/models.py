from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models, transaction
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import uuid

User = settings.AUTH_USER_MODEL

# How far ahead the availability calendar is generated.
AVAILABILITY_HORIZON_DAYS = 91

# Booking statuses that occupy inventory and therefore must not be ignored when
# counting free units.
BLOCKING_BOOKING_STATUSES = ('HELD', 'CONFIRMED', 'PENDING')


# -----------------------------
# 🏨 HOTEL MODEL
# -----------------------------
class Hotel(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hotels')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=255)
    location = gis_models.PointField(geography=True, null=True, blank=True)
    rating = models.FloatField(default=0.0)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def generate_availability(self, days: int = AVAILABILITY_HORIZON_DAYS):
        """
        Create rolling availability rows for every room type of this hotel.

        Runs on hotel creation *and* whenever a room type is added later, so a
        room type created through the API is not left with an empty calendar.
        """
        start_date = timezone.localdate()
        room_types = RoomType.objects.filter(hotel=self)

        with transaction.atomic():
            for room in room_types:
                for i in range(days):
                    date_entry = start_date + timedelta(days=i)
                    Availability.objects.get_or_create(
                        room_type=room,
                        room_unit=None,
                        date=date_entry,
                        defaults={
                            'available_units': room.total_units,
                            'price': room.base_price,
                        }
                    )


# -----------------------------
# 🛏 ROOM TYPES & UNITS
# -----------------------------
class RoomType(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='room_types')
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, null=True)
    capacity = models.PositiveIntegerField(default=1)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_units = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('hotel', 'name')

    def __str__(self):
        return f"{self.hotel.name} - {self.name}"


class RoomUnit(models.Model):
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='units')
    unit_code = models.CharField(max_length=50)  # e.g. "101", "A-1"
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('room_type', 'unit_code')

    def __str__(self):
        return f"{self.room_type} ({self.unit_code})"


# -----------------------------
# 💰 RATE PLAN
# -----------------------------
class RatePlan(models.Model):
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='rate_plans')
    name = models.CharField(max_length=120)
    price_multiplier = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal('1.0'))
    refundable = models.BooleanField(default=True)
    breakfast_included = models.BooleanField(default=False)
    discount_percent = models.FloatField(default=0.0)
    min_stay = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_final_price(self):
        """
        Nightly price after the multiplier and the discount.

        discount_percent is a FloatField, so the arithmetic has to be done in
        Decimal: ``Decimal * float`` raises TypeError, which turned any rate
        plan detail request into a 500.
        """
        base = Decimal(self.room_type.base_price) * Decimal(self.price_multiplier)
        discount = Decimal(str(self.discount_percent or 0))
        return (base * (Decimal(100) - discount) / Decimal(100)).quantize(Decimal("0.01"))

    def __str__(self):
        return f"{self.room_type} - {self.name}"


# -----------------------------
# 📅 AVAILABILITY
# -----------------------------
class Availability(models.Model):
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='availability')
    room_unit = models.ForeignKey(RoomUnit, on_delete=models.CASCADE, related_name='availability', null=True, blank=True)
    date = models.DateField()
    available_units = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_booked = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # The previous ``unique_together`` on ('room_type', 'date') and
        # ('room_unit', 'date') silently did nothing for the aggregate rows we
        # actually write: room_unit is NULL there, and in Postgres NULLs never
        # collide in a unique index, so duplicates accumulated freely.
        # These conditional constraints do enforce one row per shape.
        constraints = [
            models.UniqueConstraint(
                fields=['room_type', 'date'],
                condition=models.Q(room_unit__isnull=True),
                name='uniq_availability_room_type_date',
            ),
            models.UniqueConstraint(
                fields=['room_unit', 'date'],
                condition=models.Q(room_unit__isnull=False),
                name='uniq_availability_room_unit_date',
            ),
        ]
        indexes = [models.Index(fields=['room_type', 'date'])]

    def __str__(self):
        target = self.room_unit or self.room_type
        return f"{target} - {self.date}"


# -----------------------------
# 📘 BOOKING
# -----------------------------
class Booking(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Payment'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED', 'Expired'),
        ('HELD', 'Held'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='bookings')
    room_type = models.ForeignKey(RoomType, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    room_unit = models.ForeignKey(RoomUnit, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    rate_plan = models.ForeignKey(RatePlan, on_delete=models.SET_NULL, null=True, blank=True)
    check_in = models.DateField()
    check_out = models.DateField()
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    hold_token = models.CharField(max_length=128, null=True, blank=True)
    hold_expires_at = models.DateTimeField(null=True, blank=True)
    meta = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['status', 'hold_expires_at']),
            models.Index(fields=['user']),
        ]

    def save(self, *args, **kwargs):
        if self.status == 'PENDING' and not self.hold_expires_at:
            self.hold_expires_at = timezone.now() + timedelta(minutes=10)
        if self.meta is None:
            self.meta = {}
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking {self.id} ({self.status}) - {self.hotel.name}"

    @property
    def nights(self) -> int:
        return max((self.check_out - self.check_in).days, 0)

    def holds_inventory(self) -> bool:
        """True while this booking must be counted as occupying rooms."""
        return self.status in ('HELD', 'CONFIRMED')

    @staticmethod
    def is_available(room_type, check_in, check_out, units: int = 1) -> bool:
        """
        Whether ``room_type`` has at least ``units`` free on every night.

        Note this reads committed data only, so it is a pre-flight check. The
        authoritative, race-free version is :func:`hotels.services.hold_rooms`,
        which locks the rows. Callers that must not overbook have to use that
        one; this helper exists for read-only screens and availability search.
        """
        nights = [check_in + timedelta(days=i) for i in range((check_out - check_in).days)]
        if not nights:
            return False
        return not Availability.objects.filter(
            room_type=room_type,
            room_unit__isnull=True,
            date__in=nights,
        ).filter(available_units__lt=units).exists()