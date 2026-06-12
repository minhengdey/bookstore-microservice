from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from .models import Voucher, FlashSale
from .serializers import VoucherSerializer, FlashSaleSerializer
from .services import (
    validate_voucher,
    consume_voucher,
    get_flash_sale_prices,
    consume_flash_sale_items,
    VoucherError,
)


class VoucherViewSet(viewsets.ModelViewSet):
    queryset = Voucher.objects.all()
    serializer_class = VoucherSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("active"):
            qs = qs.filter(
                is_active=True,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now(),
            )
        return qs


class FlashSaleViewSet(viewsets.ModelViewSet):
    queryset = FlashSale.objects.prefetch_related("items").all()
    serializer_class = FlashSaleSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("active"):
            qs = qs.filter(
                is_active=True,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now(),
            )
        return qs


@api_view(["POST"])
def apply_voucher(request):
    code = request.data.get("code")
    order_amount = request.data.get("order_amount")
    if not code or order_amount is None:
        return Response(
            {"error": "Thiếu mã giảm giá hoặc giá trị đơn hàng."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        result = validate_voucher(code, order_amount)
        return Response(result)
    except VoucherError as e:
        return Response({"error": str(e)}, status=e.status_code)


@api_view(["POST"])
def consume_voucher_view(request):
    code = request.data.get("code")
    order_id = request.data.get("order_id")
    if not code:
        return Response({"error": "Thiếu mã giảm giá."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        result = consume_voucher(code, order_id=order_id)
        return Response(result)
    except VoucherError as e:
        return Response({"error": str(e)}, status=e.status_code)


@api_view(["GET"])
def flash_sale_prices(request):
    raw = request.query_params.get("product_ids", "")
    product_ids = [int(x) for x in raw.split(",") if x.strip().isdigit()]
    return Response({"prices": get_flash_sale_prices(product_ids)})


@api_view(["POST"])
def consume_flash_sale(request):
    items = request.data.get("items", [])
    if not items:
        return Response({"consumed": []})
    try:
        result = consume_flash_sale_items(items)
        return Response(result)
    except VoucherError as e:
        return Response({"error": str(e)}, status=e.status_code)
