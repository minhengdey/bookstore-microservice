"""
Tạo dữ liệu mẫu: Discount, Order, OrderItem, OrderDiscount, Invoice, Coupon.
Chạy: python manage.py seed_mock
"""
from decimal import Decimal
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from app.models import Discount, Order, OrderItem, OrderDiscount, Invoice, Coupon
from app.models.order import OrderStatus
from app.models.invoice import InvoiceStatus
from app.models.coupon import CouponStatus


class Command(BaseCommand):
    help = "Seed mock data: discounts, orders, order items, invoices, coupons"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Xóa dữ liệu cũ trước khi seed")

    def handle(self, *args, **options):
        if options.get("clear"):
            Invoice.objects.all().delete()
            OrderDiscount.objects.all().delete()
            OrderItem.objects.all().delete()
            Order.objects.all().delete()
            Coupon.objects.all().delete()
            Discount.objects.all().delete()
            self.stdout.write(self.style.WARNING("Đã xóa dữ liệu order."))

        if Order.objects.exists():
            self.stdout.write(self.style.NOTICE("Đã có dữ liệu order, bỏ qua seed."))
            return

        start = date.today()
        end = start + timedelta(days=30)
        Discount.objects.create(
            discount_code="GIAM10",
            discount_name="Giảm 10%",
            description="Áp dụng đơn từ 200k",
            start_date=start,
            end_date=end,
            discount_value=Decimal("10"),
            is_percentage=True,
            is_active=True,
        )
        Discount.objects.create(
            discount_code="FIX50K",
            discount_name="Giảm 50.000đ",
            start_date=start,
            end_date=end,
            discount_value=Decimal("50000"),
            is_percentage=False,
            is_active=True,
        )

        order1 = Order.objects.create(
            customer_id=1,
            status=OrderStatus.CONFIRMED,
            shipping_fee=Decimal("15000"),
            discount_amount=Decimal("7200"),
            total_amount=Decimal("150800"),
            admin_id=1,
            notes="",
        )
        OrderItem.objects.create(order=order1, book_id=1, quantity=2, unit_price=Decimal("72000"), discount=Decimal("0"))
        OrderItem.objects.create(order=order1, book_id=3, quantity=1, unit_price=Decimal("89000"), discount=Decimal("0"))
        OrderDiscount.objects.create(order=order1, discount_id=1, applied_value=Decimal("10"))
        Invoice.objects.create(order=order1, status=InvoiceStatus.ISSUED, due_date=date.today() + timedelta(days=7))

        order2 = Order.objects.create(
            customer_id=2,
            status=OrderStatus.DELIVERED,
            shipping_fee=Decimal("15000"),
            discount_amount=Decimal("0"),
            total_amount=Decimal("83000"),
            admin_id=1,
        )
        OrderItem.objects.create(order=order2, book_id=2, quantity=1, unit_price=Decimal("68000"), discount=Decimal("0"))
        Invoice.objects.create(order=order2, status=InvoiceStatus.PAID)

        Coupon.objects.create(
            customer_id=1,
            order_id=None,
            coupon_code="WELCOME01",
            discount_value=Decimal("15"),
            is_percentage=True,
            expiry_date=end,
            status=CouponStatus.ACTIVE,
        )

        self.stdout.write(self.style.SUCCESS("Created discounts, 2 orders with items, invoices, and 1 coupon."))
