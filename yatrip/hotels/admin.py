from django.contrib import admin
from .models import Hotel, RoomType, RatePlan, Booking, Availability

@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'created_at')
    search_fields = ('name', 'location')

@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'hotel', 'base_price', 'total_units')
    list_filter = ('hotel',)

@admin.register(RatePlan)
class RatePlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'room_type', 'refundable', 'breakfast_included', 'discount_percent')

@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ('room_type', 'date', 'available_units', 'price')
    list_filter = ('room_type',)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'room_type', 'status', 'check_in', 'check_out', 'hold_expires_at')
    list_filter = ('status',)