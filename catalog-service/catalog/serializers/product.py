from rest_framework import serializers
from catalog.models import Product
from .brand import BrandSerializer
from .category import CategorySerializer
from .image import ProductImageSerializer
from .variant import ProductVariantSerializer
from .review import ReviewSerializer
from catalog.services.storage_service import StorageService

class ProductListSerializer(serializers.ModelSerializer):
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'thumbnail', 'min_price', 'max_price', 'is_active']

    def get_thumbnail(self, obj):
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            return StorageService.get_presigned_url(primary.image_key)
        return None

class ProductDetailSerializer(ProductListSerializer):
    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    # reviews will be paginated separately or included if small enough

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + ['description', 'brand', 'category', 'images', 'variants', 'created_at']
