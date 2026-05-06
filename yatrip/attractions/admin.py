from django.contrib import admin
from .models import Attraction


@admin.register(Attraction)
class AttractionAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'city', 'state', 'rating', 'is_free', 'is_active', 'created_at']
    list_filter = ['category', 'is_free', 'is_active', 'country', 'state']
    search_fields = ['name', 'city', 'state', 'description']
    readonly_fields = ['osm_id', 'osm_type', 'created_at', 'updated_at']
    list_editable = ['is_active']
    ordering = ['-created_at']

    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'description', 'category', 'is_active')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude', 'address', 'city', 'state', 'country')
        }),
        ('Details', {
            'fields': ('rating', 'review_count', 'image_url', 'website', 'phone', 'opening_hours', 'entry_fee', 'is_free')
        }),
        ('OSM Data', {
            'fields': ('osm_id', 'osm_type'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )