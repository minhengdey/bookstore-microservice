from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VoucherViewSet, FlashSaleViewSet, apply_voucher

router = DefaultRouter()
router.register(r'vouchers', VoucherViewSet)
router.register(r'flash-sales', FlashSaleViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('apply-voucher/', apply_voucher, name='apply_voucher'),
]
