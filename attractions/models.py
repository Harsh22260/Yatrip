from django.contrib.gis.db import models

class Attraction(models.Model):
    CATEGORY_CHOICES = [
        ('monument', 'Monument'),
        ('temple', 'Temple'),
        ('park', 'Park'),
        ('museum', 'Museum'),
        ('nature', 'Nature'),
        ('other', 'Other'),
    ]
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    address = models.CharField(max_length=255, blank=True, null=True)
    location = models.PointField(geography=True, null=True, blank=True)
    image = models.ImageField(upload_to='attraction_images/', null=True, blank=True)
    entry_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.city})"