from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models, transaction
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import uuid

User = settings.AUTH_USER_MODEL


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

    def generate_availability(self):
        """Auto-create 90 days of availability data for each room type"""
        start_date = date.today()
        room_types = RoomType.objects.filter(hotel=self)

        with transaction.atomic():
            for room in room_types:
                for i in range(91):
                    date_entry = start_date + timedelta(days=i)
                    Availability.objects.get_or_create(
                        room_type=room,
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
        """Calculate final price after multiplier and discount"""
        base = self.room_type.base_price * self.price_multiplier
        return base * (1 - self.discount_percent / 100)

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
        unique_together = (('room_type', 'date'), ('room_unit', 'date'))

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
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking {self.id} ({self.status}) - {self.hotel.name}"

    @staticmethod
    def is_available(room_type, check_in, check_out):
        return not Availability.objects.filter(
            room_type=room_type,
            date__range=[check_in, check_out],
            available_units__lte=0
        ).exists()