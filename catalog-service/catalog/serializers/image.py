from rest_framework import serializers
from catalog.models import ProductImage
from catalog.services.storage_service import StorageService

class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ['id', 'product', 'variant', 'image_key', 'url', 'alt_text', 'is_primary']

    def get_url(self, obj):
        return StorageService.get_presigned_url(obj.image_key)
