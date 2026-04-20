from rest_framework import serializers

class ProductSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=255)
    title = serializers.CharField(source='name') # Alias for legacy services
    category_id = serializers.IntegerField()
    price_amount = serializers.DecimalField(max_digits=12, decimal_places=2, source='price.amount')
    sale_price = serializers.DecimalField(max_digits=12, decimal_places=2, source='price.amount') # Alias for legacy services
    currency = serializers.CharField(source='price.currency', default='VND')
    sku_value = serializers.CharField(source='sku.value')
    attributes = serializers.DictField(source='attributes.data')
    description = serializers.CharField(allow_blank=True, default='')
    status = serializers.CharField(default='active')
