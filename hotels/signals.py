from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Hotel

@receiver(post_save, sender=Hotel)
def auto_generate_availability(sender, instance, created, **kwargs):
    if created:
        instance.generate_availability()