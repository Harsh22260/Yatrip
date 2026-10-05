from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from yatrip.auth import clear_auth_cookies, set_auth_cookies

from .models import OwnerProfile
from .serializers import OwnerProfileSerializer, RegisterSerializer, UserSerializer

User = get_user_model()


class CookieTokenObtainPairView(TokenObtainPairView):
    """
    Log in, and hand the tokens to the browser as HttpOnly cookies.

    The token is still in the response body so nothing that expects the old
    shape breaks, but the SPA no longer has to keep a copy in localStorage.
    """

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        access = response.data.get("access")
        refresh = response.data.get("refresh")
        if access:
            set_auth_cookies(response, access, refresh, request=request)
        return response


class CookieTokenRefreshView(TokenRefreshView):
    """Rotate the access token and re-set the cookie with the new value."""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        access = response.data.get("access")
        refresh = response.data.get("refresh")
        if access:
            set_auth_cookies(response, access, refresh, request=request)
        return response


class LogoutView(generics.GenericAPIView):
    """
    Drop the session.

    Both the cookies and the rotating refresh token are cleared. Blacklisting
    the refresh token matters as much as deleting the cookie: otherwise a token
    that was already copied out of the browser stays valid until it expires.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        raw = request.COOKIES.get("yatrip_refresh")
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except Exception:  # noqa: BLE001 - already expired or invalid
                pass
        response = Response({"detail": "Signed out."})
        clear_auth_cookies(response)
        return response


# Register new user
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


# Get current user profile
class UserProfileView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class OwnerProfileView(generics.RetrieveUpdateAPIView):
    """
    View or update the caller's own owner profile.

    ``get_object`` used ``OwnerProfile.objects.get(user=...)``, which raised
    DoesNotExist and surfaced as a 500 for every user who had not completed the
    owner form. The profile is now created on demand, and a POST route exists so
    the profile can also be created explicitly.
    """

    serializer_class = OwnerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, _created = OwnerProfile.objects.get_or_create(
            user=self.request.user,
            defaults={"business_name": "", "business_type": "hotel", "address": "", "contact_number": ""},
        )
        return profile


class OwnerProfileCreateView(generics.CreateAPIView):
    """
    Create (or top up) the caller's owner profile.

    Upsert rather than a strict 409: ``OwnerProfileView`` already provisions an
    empty profile on first GET so the edit form has something to bind to, which
    would otherwise make this route fail with a conflict immediately after the
    user visited the profile page.
    """

    serializer_class = OwnerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        # is_approved is read-only, so an owner cannot self-approve.
        if self.request.user.is_staff:
            serializer.fields["is_approved"].read_only = False
        return serializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        existing = OwnerProfile.objects.filter(user=request.user).first()
        if existing is None:
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        # Update in place. Calling save(user=...) here would attempt a second
        # INSERT and fail on the one-to-one constraint.
        serializer.instance = existing
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
