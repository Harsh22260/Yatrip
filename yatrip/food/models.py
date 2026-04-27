from django.contrib.gis.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class FoodCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    def __str__(self):
        return self.name


class FoodVendor(models.Model):
    VENDOR_TYPE = [
        ('registered', 'Registered Vendor'),
        ('street', 'Local Street Vendor'),
    ]

    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='food_vendors')
    name = models.CharField(max_length=200)
    vendor_type = models.CharField(max_length=20, choices=VENDOR_TYPE, default='registered')
    description = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=255)
    location = models.PointField(geography=True, null=True, blank=True)
    avg_cost = models.DecimalField(max_digits=8, decimal_places=2)
    rating = models.FloatField(default=0.0)
    is_verified = models.BooleanField(default=False)
    category = models.ForeignKey(FoodCategory, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_vendor_type_display()})"


class FoodImage(models.Model):
    vendor = models.ForeignKey(FoodVendor, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='food_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


class MenuItem(models.Model):
    vendor = models.ForeignKey(FoodVendor, on_delete=models.CASCADE, related_name='menu_items')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_available = models.BooleanField(default=True)
    image = models.ImageField(upload_to='menu_images/', null=True, blank=True)

    def __str__(self):
        return f"{self.name} - ₹{self.price}"