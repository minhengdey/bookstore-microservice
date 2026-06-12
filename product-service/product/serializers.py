from rest_framework import serializers
from .models import Product, Category, ProductVariant, Brand, InventoryTransaction

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = "__all__"

class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = "__all__"

class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)
    brand = BrandSerializer(read_only=True)
    brand_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    effective_price = serializers.SerializerMethodField()
    list_price = serializers.DecimalField(source="price", max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = "__all__"

    def get_effective_price(self, obj):
        obj.refresh_flash_sale_state(save=True)
        return obj.effective_price

class InventoryTransactionSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    variant_name = serializers.CharField(source='variant.__str__', read_only=True)

    class Meta:
        model = InventoryTransaction
        fields = "__all__"
