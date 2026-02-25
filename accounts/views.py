from rest_framework import generics, permissions
from django.contrib.auth import get_user_model
from .models import OwnerProfile
from .serializers import RegisterSerializer, UserSerializer, OwnerProfileSerializer

User = get_user_model()

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


# Owner profile create/view
class OwnerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = OwnerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return OwnerProfile.objects.get(user=self.request.user)