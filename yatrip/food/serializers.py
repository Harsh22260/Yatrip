from rest_framework import serializers
from .models import FoodVendor, FoodImage, MenuItem, FoodCategory

class FoodImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodImage
        fields = ['id', 'image', 'uploaded_at']


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'description', 'price', 'is_available', 'image']


class FoodCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodCategory
        fields = ['id', 'name', 'description']


class FoodVendorSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    images = FoodImageSerializer(many=True, read_only=True)
    menu_items = MenuItemSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = FoodVendor
        fields = [
            'id', 'owner_email', 'name', 'vendor_type', 'description',
            'address', 'location', 'avg_cost', 'rating', 'is_verified',
            'created_at', 'category', 'category_name', 'images', 'menu_items'
        ]