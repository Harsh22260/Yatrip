from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from .models import OwnerProfile

User = get_user_model()


def _username_from_email(email: str) -> str:
    """Build a unique, Django-safe username from an email address."""
    base = (email.split("@")[0] or "user").lower()
    cleaned = "".join(ch for ch in base if ch.isalnum() or ch in "._-")[:140] or "user"
    candidate = cleaned
    suffix = 1
    while User.objects.filter(username=candidate).exists():
        suffix += 1
        candidate = f"{cleaned}{suffix}"
    return candidate


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username", "phone", "is_owner", "is_verified", "created_at"]
        # is_verified is an admin decision; it was writable here.
        read_only_fields = ["id", "email", "username", "is_verified", "created_at"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)
    # The model's username is not blank=True, so DRF made it mandatory and
    # registration failed for anyone who only sent an email. It is derived from
    # the address when omitted.
    username = serializers.CharField(required=False, max_length=150, allow_blank=True)
    # Owner details arrive with the signup form, so they are accepted here and
    # written atomically below. Previously the frontend collected them and they
    # were silently dropped, leaving the account with no OwnerProfile at all.
    business_name = serializers.CharField(write_only=True, required=False, max_length=200)
    business_type = serializers.ChoiceField(
        write_only=True, required=False, choices=OwnerProfile._meta.get_field("business_type").choices
    )
    business_address = serializers.CharField(write_only=True, required=False)
    contact_number = serializers.CharField(write_only=True, required=False, max_length=15)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "password",
            "phone",
            "is_owner",
            "business_name",
            "business_type",
            "business_address",
            "contact_number",
        ]

    def validate_email(self, value):
        value = (value or "").strip().lower()
        if not value:
            raise serializers.ValidationError("Email is required.")
        if User.objects.filter(email__iexact=value).exists():
            # Without this the save() raised IntegrityError and the API returned
            # 500 for what is really a duplicate-account conflict.
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        wants_owner = bool(attrs.get("is_owner"))
        if wants_owner:
            missing = [
                name
                for name in ("business_name", "business_type", "business_address", "contact_number")
                if not attrs.get(name)
            ]
            if missing:
                raise serializers.ValidationError(
                    {name: "This field is required to register as an owner." for name in missing}
                )
        return attrs

    def validate_password(self, value):
        validate_password(value)
        return value

    @transaction.atomic
    def create(self, validated_data):
        profile_fields = {
            "business_name": validated_data.pop("business_name", None),
            "business_type": validated_data.pop("business_type", None),
            "business_address": validated_data.pop("business_address", None),
            "contact_number": validated_data.pop("contact_number", None),
        }
        wants_owner = bool(validated_data.pop("is_owner", False))
        password = validated_data.pop("password")

        email = validated_data["email"]
        username = (validated_data.get("username") or "").strip() or _username_from_email(email)

        # email/username are already present in validated_data, so they are
        # overwritten in place rather than passed twice.
        validated_data["email"] = email
        validated_data["username"] = username
        user = User(**validated_data, is_owner=wants_owner)
        user.set_password(password)
        # is_verified/is_owner must never be trusted from the request body.
        user.is_verified = False
        user.save()

        if wants_owner:
            OwnerProfile.objects.create(
                user=user,
                business_name=profile_fields["business_name"],
                business_type=profile_fields["business_type"],
                address=profile_fields["business_address"],
                contact_number=profile_fields["contact_number"],
                # Approval is a staff decision and always starts false.
                is_approved=False,
            )
        return user


class OwnerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    business_type_display = serializers.CharField(source="get_business_type_display", read_only=True)

    class Meta:
        model = OwnerProfile
        fields = [
            "id",
            "user",
            "business_name",
            "business_type",
            "business_type_display",
            "address",
            "contact_number",
            # Approval is granted by staff. With fields='__all__' and a
            # RetrieveUpdateAPIView an owner could PATCH is_approved to true and
            # approve their own business.
            "is_approved",
        ]
        read_only_fields = ["id", "user", "is_approved"]
