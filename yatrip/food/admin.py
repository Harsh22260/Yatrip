from django.contrib import admin
from .models import FoodPlace

@admin.register(FoodPlace)
class FoodPlaceAdmin(admin.ModelAdmin):
    list_display  = ['name', 'category', 'cuisine', 'city', 'rating', 'price_level', 'is_veg', 'is_active']
    list_filter   = ['category', 'cuisine', 'is_veg', 'is_active', 'price_level']
    search_fields = ['name', 'city', 'state', 'description']
    list_editable = ['is_active']
    readonly_fields = ['osm_id', 'osm_type', 'created_at', 'updated_at']