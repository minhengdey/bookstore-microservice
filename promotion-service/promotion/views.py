from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Voucher, FlashSale
from .serializers import VoucherSerializer, FlashSaleSerializer
from django.utils import timezone

class VoucherViewSet(viewsets.ModelViewSet):
    queryset = Voucher.objects.all()
    serializer_class = VoucherSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('active'):
            qs = qs.filter(is_active=True, start_date__lte=timezone.now(), end_date__gte=timezone.now())
        return qs

class FlashSaleViewSet(viewsets.ModelViewSet):
    queryset = FlashSale.objects.all()
    serializer_class = FlashSaleSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('active'):
            qs = qs.filter(is_active=True, start_date__lte=timezone.now(), end_date__gte=timezone.now())
        return qs

@api_view(['POST'])
def apply_voucher(request):
    code = request.data.get('code')
    order_amount = request.data.get('order_amount')
    
    if not code or order_amount is None:
        return Response({'error': 'Missing code or order_amount'}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        voucher = Voucher.objects.get(code=code, is_active=True)
    except Voucher.DoesNotExist:
        return Response({'error': 'Invalid voucher code'}, status=status.HTTP_404_NOT_FOUND)
        
    now = timezone.now()
    if now < voucher.start_date or now > voucher.end_date:
        return Response({'error': 'Voucher expired or not started yet'}, status=status.HTTP_400_BAD_REQUEST)
        
    if voucher.used_count >= voucher.usage_limit:
        return Response({'error': 'Voucher usage limit reached'}, status=status.HTTP_400_BAD_REQUEST)
        
    order_amount = float(order_amount)
    if order_amount < float(voucher.min_order_value):
        return Response({'error': f'Minimum order value is {voucher.min_order_value}'}, status=status.HTTP_400_BAD_REQUEST)
        
    discount = 0
    if voucher.discount_percentage:
        discount = order_amount * float(voucher.discount_percentage) / 100.0
        if voucher.max_discount_amount and discount > float(voucher.max_discount_amount):
            discount = float(voucher.max_discount_amount)
    elif voucher.discount_amount:
        discount = float(voucher.discount_amount)
        
    return Response({
        'code': voucher.code,
        'discount_amount': discount,
        'final_amount': order_amount - discount
    })
