from django.db import models


class EnrichmentCache(models.Model):
    """
    Cache for place enrichment (image, rating, opening hours).

    ``payload`` holds a partial dict such as
    ``{"image_url": ..., "source": "opentripmap"}``. A row with ``found=False``
    is a cached *miss*: without it, a place that has no photo on any upstream
    would re-query Wikipedia on every single page view.
    """

    #: Either "geo:12.9716,77.5946" or "name:brigade road|bengaluru".
    key = models.CharField(max_length=255, unique=True)

    payload = models.JSONField(default=dict, blank=True)
    source = models.CharField(max_length=32, blank=True, default="")

    found = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "enrichment_cache"
        indexes = [models.Index(fields=["expires_at"], name="enrich_exp_idx")]

    def __str__(self):
        state = "hit" if self.found else "miss"
        return f"{self.key} ({state}, {self.source or 'none'})"


class SyncState(models.Model):
    """
    Progress marker for the resumable OSM ingestion sweep.

    The sweep walks a long list of settlements across India. Storing the last
    completed index means an interrupted run resumes instead of restarting, and
    the elapsed/remaining counters can be reported to the operator.
    """

    #: e.g. "attractions", "food", "transport"
    dataset = models.CharField(max_length=32, unique=True)

    last_settlement_index = models.IntegerField(default=0)
    settlements_total = models.IntegerField(default=0)
    places_total = models.IntegerField(default=0)

    status = models.CharField(max_length=16, default="idle")
    last_error = models.TextField(blank=True, default="")

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sync_state"

    def __str__(self):
        return f"{self.dataset} {self.status} {self.last_settlement_index}/{self.settlements_total}"


class Settlement(models.Model):
    """
    An Indian settlement used to drive the OSM ingestion sweep.

    Kept in the database (rather than a hard-coded list) so coverage can grow
    without a code change, and so the sweep can be ordered by population and
    resumed after an interruption.
    """

    name = models.CharField(max_length=200)
    place_type = models.CharField(max_length=20, default="town")

    latitude = models.FloatField()
    longitude = models.FloatField()

    population = models.IntegerField(null=True, blank=True)
    state = models.CharField(max_length=100, blank=True, default="")

    osm_id = models.CharField(max_length=64, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "settlement"
        indexes = [
            models.Index(fields=["-population"], name="settlement_pop_idx"),
            models.Index(fields=["name"], name="settlement_name_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.place_type}, pop={self.population})"
