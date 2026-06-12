from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VoucherViewSet,
    FlashSaleViewSet,
    apply_voucher,
    consume_voucher_view,
    flash_sale_prices,
    consume_flash_sale,
)

router = DefaultRouter()
router.register(r"vouchers", VoucherViewSet)
router.register(r"flash-sales", FlashSaleViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("apply-voucher/", apply_voucher, name="apply_voucher"),
    path("consume-voucher/", consume_voucher_view, name="consume_voucher"),
    path("flash-sale-prices/", flash_sale_prices, name="flash_sale_prices"),
    path("consume-flash-sale/", consume_flash_sale, name="consume_flash_sale"),
]
