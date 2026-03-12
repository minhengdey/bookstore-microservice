"""
Tạo dữ liệu mẫu: ShippingMethod, ShippingFeature, Shipping, ShippingAddress, ShippingStatus.
Giả định order-service đã seed (order_id 1, 2).
Chạy: python manage.py seed_mock
"""
from decimal import Decimal
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from app.models import ShippingMethod, ShippingFeature, Shipping, ShippingAddress, ShippingStatus


class Command(BaseCommand):
    help = "Seed mock data: shipping methods, shippings, addresses, statuses"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Xóa dữ liệu cũ trước khi seed")

    def handle(self, *args, **options):
        if options.get("clear"):
            ShippingStatus.objects.all().delete()
            ShippingAddress.objects.all().delete()
            Shipping.objects.all().delete()
            ShippingFeature.objects.all().delete()
            ShippingMethod.objects.all().delete()
            self.stdout.write(self.style.WARNING("Đã xóa dữ liệu ship."))

        if ShippingMethod.objects.exists():
            self.stdout.write(self.style.NOTICE("Đã có dữ liệu ship, bỏ qua seed."))
            return

        sm1 = ShippingMethod.objects.create(
            method_name="Giao hàng tiêu chuẩn",
            description="3-5 ngày",
            min_weight=0,
            max_weight=5000,
            min_distance=0,
            max_distance=500,
            rate=Decimal("15000"),
        )
        ShippingFeature.objects.create(shipping_method=sm1, feature="speed", value="3-5 days")
        sm2 = ShippingMethod.objects.create(
            method_name="Giao hàng nhanh",
            description="1-2 ngày",
            rate=Decimal("30000"),
        )
        ShippingFeature.objects.create(shipping_method=sm2, feature="speed", value="1-2 days")

        for order_id, city in [(1, "TP.HCM"), (2, "Hà Nội")]:
            ship = Shipping.objects.create(
                order_id=order_id,
                shipping_method=sm1,
                status="delivered" if order_id == 2 else "shipped",
                estimated_delivery_date=date.today() + timedelta(days=3),
            )
            ShippingAddress.objects.create(
                shipping=ship,
                recipient_name=f"Customer {order_id}",
                address_line="123 Đường ABC",
                city=city,
                state="",
                country="Vietnam",
                postal_code="700000" if city == "TP.HCM" else "100000",
                phone="0900000000",
            )
            ShippingStatus.objects.create(shipping=ship, status=ship.status, description="Đã giao" if ship.status == "delivered" else "Đang giao")

        self.stdout.write(self.style.SUCCESS("Created shipping methods, 2 shippings with addresses and statuses."))
