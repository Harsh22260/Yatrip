from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Hotel, RoomType


@receiver(post_save, sender=Hotel)
def auto_generate_availability(sender, instance, created, **kwargs):
    if created:
        instance.generate_availability()


@receiver(post_save, sender=RoomType)
def auto_generate_availability_for_room_type(sender, instance, created, **kwargs):
    """
    Give a newly added room type its own availability calendar.

    Only Hotel post_save was wired up, so a room type created later through the
    API (or admin) had no Availability rows at all and could never be booked.
    """
    if not created:
        return
    if instance.total_units < 0:
        return
    instance.hotel.generate_availability()
