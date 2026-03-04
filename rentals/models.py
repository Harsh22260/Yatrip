from django.contrib.gis.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class RentalAmenity(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Rental(models.Model):
    RENTAL_TYPES = [
        ('homestay', 'Homestay'),
        ('pg', 'Paying Guest'),
        ('hostel', 'Hostel'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rentals')
    name = models.CharField(max_length=200)
    rental_type = models.CharField(max_length=50, choices=RENTAL_TYPES)
    description = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=255)
    location = models.PointField(geography=True, null=True, blank=True)
    price_per_month = models.DecimalField(max_digits=10, decimal_places=2)
    is_verified = models.BooleanField(default=False)
    available_rooms = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    amenities = models.ManyToManyField(RentalAmenity, related_name='rentals', blank=True)

    def __str__(self):
        return f"{self.name} – {self.get_rental_type_display()}"


class RentalImage(models.Model):
    rental = models.ForeignKey(Rental, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='rental_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)