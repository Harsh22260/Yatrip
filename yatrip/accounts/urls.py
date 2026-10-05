from django.urls import path
from .views import (
    OwnerProfileCreateView,
    OwnerProfileView,
    RegisterView,
    UserProfileView,
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    LogoutView,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    # The cookie variants are the ones the SPA uses: they return the same token
    # payload but also set it as HttpOnly cookies. The plain SimpleJWT views
    # stay wired for scripts and the test client.
    path('login/', CookieTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    # Explicit create route: the view is RetrieveUpdate, so POSTing a profile
    # used to be a 405 and non-owners had no way to become one.
    path('owner/', OwnerProfileView.as_view(), name='owner_profile'),
    path('owner/create/', OwnerProfileCreateView.as_view(), name='owner_profile_create'),
]