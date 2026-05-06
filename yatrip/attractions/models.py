from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import math
 
 
class AttractionCategory(models.TextChoices):
    ALL = 'all', 'All'
    MONUMENT = 'monument', 'Monument'
    TEMPLE = 'temple', 'Temple'
    PARK = 'park', 'Park'
    MUSEUM = 'museum', 'Museum'
    NATURE = 'nature', 'Nature'
    OTHER = 'other', 'Other'
 
 
class Attraction(models.Model):
    # Basic Info
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    category = models.CharField(
        max_length=20,
        choices=AttractionCategory.choices,
        default=AttractionCategory.OTHER
    )
 
    # Location
    latitude = models.FloatField()
    longitude = models.FloatField()
    address = models.CharField(max_length=500, blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    state = models.CharField(max_length=100, blank=True, default='')
    country = models.CharField(max_length=100, default='India')
 
    # Details
    rating = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    review_count = models.IntegerField(default=0)
    image_url = models.URLField(blank=True, default='')
    website = models.URLField(blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    opening_hours = models.JSONField(default=dict, blank=True)
    entry_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_free = models.BooleanField(default=True)
 
    # OSM Data
    osm_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    osm_type = models.CharField(max_length=20, blank=True, default='')
 
    # Meta
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    class Meta:
        db_table = 'attractions'
        ordering = ['-rating', '-review_count']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['city']),
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['osm_id']),
        ]
 
    def __str__(self):
        return f"{self.name} ({self.city})"
 
    def distance_from(self, lat, lon):
        """Haversine formula - returns distance in km"""
        R = 6371
        lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
        lat2, lon2 = math.radians(lat), math.radians(lon)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c