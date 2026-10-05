from django.contrib.gis.db import models


class TransportNode(models.Model):
    """
    A local transport hub: bus stand, auto stand, metro station, railway
    station, airport or shared-taxi point.

    The proposal is specifically about *local* transport, so bus and auto
    stands matter as much as metro and rail. The original model had four types,
    no railway or airport, and no imagery, so the transport tab rendered an
    empty screen with nothing to distinguish one node from another.
    """

    class NodeType(models.TextChoices):
        BUS = "bus", "Bus Stand"
        AUTO = "auto", "Auto Stand"
        METRO = "metro", "Metro Station"
        RAIL = "rail", "Railway Station"
        AIRPORT = "airport", "Airport"
        TAXI = "taxi", "Shared Taxi / Cab Stand"
        FERRY = "ferry", "Ferry Terminal"
        OTHER = "other", "Other"

    name = models.CharField(max_length=200)
    node_type = models.CharField(max_length=20, choices=NodeType.choices, default=NodeType.BUS)

    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=100, blank=True, default="")
    address = models.CharField(max_length=255, blank=True, null=True)

    location = models.PointField(geography=True)

    # ---- enrichment -----------------------------------------------------
    #: Same guarantee as the catalogue: every node gets an image, either a
    #: real one or category artwork supplied by the frontend fallback.
    image_url = models.URLField(max_length=600, blank=True, default="")
    image_credit = models.CharField(max_length=300, blank=True, default="")

    #: Services actually present at the hub, e.g. ["waiting_room", "atm"].
    amenities = models.JSONField(default=list, blank=True)

    #: Operator, e.g. "BMTC", "KSRTC", "Namma Metro", "Indian Railways".
    operator = models.CharField(max_length=120, blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")

    opening_hours = models.JSONField(default=dict, blank=True)

    #: Bus/taxi routes serving this hub, as OSM route refs.
    route_refs = models.JSONField(default=list, blank=True)

    #: IATA / railway code when known.
    code = models.CharField(max_length=20, blank=True, default="")

    #: True while the hub is a candidate, false once a human deletes it.
    is_active = models.BooleanField(default=True)

    osm_id = models.CharField(max_length=64, unique=True, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "transport_node"
        indexes = [
            models.Index(fields=["node_type"], name="transport_type_idx"),
            models.Index(fields=["city"], name="transport_city_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_node_type_display()})"
