from rest_framework import serializers
from .models import Voucher, FlashSale, FlashSaleItem

class VoucherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voucher
        fields = '__all__'

class FlashSaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlashSaleItem
        fields = '__all__'

class FlashSaleSerializer(serializers.ModelSerializer):
    items = FlashSaleItemSerializer(many=True, read_only=True)

    class Meta:
        model = FlashSale
        fields = '__all__'
