from django.contrib.gis.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class Amenity(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Hotel(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hotels')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=255)
    location = models.PointField(geography=True, null=True, blank=True)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    rating = models.FloatField(default=0.0)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    amenities = models.ManyToManyField(Amenity, through='HotelAmenity', related_name='hotels')

    def __str__(self):
        return self.name


class HotelAmenity(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE)
    amenity = models.ForeignKey(Amenity, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('hotel', 'amenity')


class HotelImage(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='hotel_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


class Room(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='rooms')
    room_type = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.hotel.name} - {self.room_type}"


class HotelPolicy(models.Model):
    hotel = models.OneToOneField(Hotel, on_delete=models.CASCADE, related_name='policy')
    check_in = models.TimeField()
    check_out = models.TimeField()
    cancellation_policy = models.TextField(blank=True, null=True)
    extra_guest_charge = models.DecimalField(max_digits=6, decimal_places=2, default=0)