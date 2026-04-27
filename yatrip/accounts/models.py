from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

# Custom User Model
class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    is_owner = models.BooleanField(default=False)  # Hotel / Food / Rental owner
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email


# Owner Profile – details for business owners
class OwnerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="owner_profile")
    business_name = models.CharField(max_length=200)
    business_type = models.CharField(max_length=100, choices=[
        ('hotel', 'Hotel'),
        ('rental', 'Rental'),
        ('food', 'Food'),
    ])
    address = models.TextField()
    contact_number = models.CharField(max_length=15)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.business_name} ({self.user.email})"