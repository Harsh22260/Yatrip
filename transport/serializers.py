from rest_framework import serializers
from .models import TransportNode

class TransportNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportNode
        fields = ['id', 'name', 'node_type', 'city', 'address', 'location', 'created_at']