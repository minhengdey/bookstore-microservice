"""
Tạo dữ liệu mẫu: Cart, CartItem.
Giả định customer-service đã seed (customer_id 1,2,3), book-service đã seed (book_id 1-5).
Chạy: python manage.py seed_mock
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from app.models import Cart, CartItem


class Command(BaseCommand):
    help = "Seed mock data: carts and cart items"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Xóa dữ liệu cũ trước khi seed")

    def handle(self, *args, **options):
        if options.get("clear"):
            CartItem.objects.all().delete()
            Cart.objects.all().delete()
            self.stdout.write(self.style.WARNING("Đã xóa dữ liệu cart."))

        if Cart.objects.exists():
            self.stdout.write(self.style.NOTICE("Đã có dữ liệu cart, bỏ qua seed."))
            return

        for cid in [1, 2, 3]:
            cart = Cart.objects.create(customer_id=cid)
            if cid == 1:
                CartItem.objects.create(cart=cart, book_id=1, quantity=2, unit_price=Decimal("72000"))
                CartItem.objects.create(cart=cart, book_id=3, quantity=1, unit_price=Decimal("89000"))
            elif cid == 2:
                CartItem.objects.create(cart=cart, book_id=2, quantity=1, unit_price=Decimal("68000"))

        self.stdout.write(self.style.SUCCESS("Created 3 carts with sample items (customer 1,2,3)."))
