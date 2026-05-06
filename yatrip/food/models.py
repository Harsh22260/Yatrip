from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import math


class FoodCategory(models.TextChoices):
    ALL          = 'all',           'All'
    STREET_FOOD  = 'street_food',   'Street Food'
    RESTAURANT   = 'restaurant',    'Restaurant'
    CAFE         = 'cafe',          'Café'
    DHABA        = 'dhaba',         'Dhaba'
    BAKERY       = 'bakery',        'Bakery'
    SWEET_SHOP   = 'sweet_shop',    'Sweet Shop'
    JUICE_BAR    = 'juice_bar',     'Juice Bar'
    FAST_FOOD    = 'fast_food',     'Fast Food'
    OTHER        = 'other',         'Other'


class CuisineType(models.TextChoices):
    NORTH_INDIAN  = 'north_indian',  'North Indian'
    SOUTH_INDIAN  = 'south_indian',  'South Indian'
    CHINESE       = 'chinese',       'Chinese'
    MUGHLAI       = 'mughlai',       'Mughlai'
    PUNJABI       = 'punjabi',       'Punjabi'
    RAJASTHANI    = 'rajasthani',    'Rajasthani'
    BENGALI       = 'bengali',       'Bengali'
    GUJARATI      = 'gujarati',      'Gujarati'
    CONTINENTAL   = 'continental',   'Continental'
    ITALIAN       = 'italian',       'Italian'
    STREET        = 'street',        'Street Food'
    MULTI         = 'multi',         'Multi-Cuisine'
    OTHER         = 'other',         'Other'


class FoodPlace(models.Model):
    # Basic
    name        = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    category    = models.CharField(max_length=20, choices=FoodCategory.choices, default=FoodCategory.OTHER)
    cuisine     = models.CharField(max_length=20, choices=CuisineType.choices, default=CuisineType.OTHER)

    # Location
    latitude    = models.FloatField()
    longitude   = models.FloatField()
    address     = models.CharField(max_length=500, blank=True, default='')
    city        = models.CharField(max_length=100, blank=True, default='')
    state       = models.CharField(max_length=100, blank=True, default='')
    country     = models.CharField(max_length=100, default='India')

    # Details
    rating          = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    review_count    = models.IntegerField(default=0)
    price_level     = models.IntegerField(default=1, choices=[(1,'₹'),(2,'₹₹'),(3,'₹₹₹'),(4,'₹₹₹₹')])
    avg_cost_for_two = models.IntegerField(null=True, blank=True)
    image_url       = models.URLField(blank=True, default='')
    website         = models.URLField(blank=True, default='')
    phone           = models.CharField(max_length=30, blank=True, default='')
    opening_hours   = models.JSONField(default=dict, blank=True)

    # Features
    is_veg          = models.BooleanField(null=True, blank=True)   # None = both
    is_open_now     = models.BooleanField(default=True)
    home_delivery   = models.BooleanField(default=False)
    takeaway        = models.BooleanField(default=False)
    outdoor_seating = models.BooleanField(default=False)

    # OSM
    osm_id   = models.CharField(max_length=50, unique=True, null=True, blank=True)
    osm_type = models.CharField(max_length=20, blank=True, default='')

    # Meta
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'food_places'
        ordering = ['-rating', '-review_count']
        indexes  = [
            models.Index(fields=['category']),
            models.Index(fields=['city']),
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['osm_id']),
            models.Index(fields=['cuisine']),
        ]

    def __str__(self):
        return f"{self.name} ({self.city})"

    def distance_from(self, lat, lon):
        R = 6371
        lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
        lat2, lon2 = math.radians(lat), math.radians(lon)
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))