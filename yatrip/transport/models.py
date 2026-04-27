from django.contrib.gis.db import models

class TransportNode(models.Model):
    NODE_TYPES = [
        ('bus', 'Bus Stand'),
        ('auto', 'Auto Stand'),
        ('metro', 'Metro Station'),
        ('taxi', 'Taxi Stand'),
    ]
    name = models.CharField(max_length=200)
    node_type = models.CharField(max_length=20, choices=NODE_TYPES)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=255, blank=True, null=True)
    location = models.PointField(geography=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_node_type_display()})"