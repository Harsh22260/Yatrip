from rest_framework import serializers

from .models import TransportNode


class TransportNodeSerializer(serializers.ModelSerializer):
    node_type_display = serializers.CharField(
        source="get_node_type_display", read_only=True
    )
    location = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()
    image_credit = serializers.CharField(read_only=True)

    class Meta:
        model = TransportNode
        fields = [
            "id",
            "name",
            "node_type",
            "node_type_display",
            "city",
            "state",
            "address",
            "location",
            "latitude",
            "longitude",
            "distance_km",
            "image_url",
            "image_credit",
            "amenities",
            "operator",
            "phone",
            "opening_hours",
            "route_refs",
            "code",
            "created_at",
        ]
        read_only_fields = fields

    def get_location(self, obj):
        """GeoJSON for the point, built by hand.

        Left to DRF, a GEOS Point is rendered through
        ``GEOSGeometry.__geo_interface__``, which reparses the hex EWKB string
        on every row. Profiling one 300-row page put 6.3s of a 7.0s total
        inside ``django/contrib/gis/geos/geometry.py`` while the database read
        itself took 0.03s, so serialisation, not the query, was the reason the
        hub list took well over a minute.

        The shape is byte-for-byte what the frontend's ``parseLocation``
        already expects, at effectively no cost.
        """
        if not obj.location:
            return None
        return {"type": "Point", "coordinates": [obj.location.x, obj.location.y]}

    def get_latitude(self, obj):
        return obj.location.y if obj.location else None

    def get_longitude(self, obj):
        return obj.location.x if obj.location else None

    def get_distance_km(self, obj):
        return getattr(obj, "distance_km", None)
