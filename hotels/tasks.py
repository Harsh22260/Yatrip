from django.utils import timezone
from .models import Booking

def expire_pending_bookings():
    """Mark pending bookings as expired if hold time passed"""
    now = timezone.now()
    expired = Booking.objects.filter(status='PENDING', hold_expires_at__lt=now)
    count = expired.count()
    for b in expired:
        b.status = 'EXPIRED'
        b.save()
    return f"Expired {count} pending bookings"