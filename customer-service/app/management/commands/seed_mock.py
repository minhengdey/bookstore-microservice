"""
Tạo dữ liệu mẫu: User, Customer, WebAddress.
Chạy: python manage.py seed_mock
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from app.models import User, Customer, WebAddress


class Command(BaseCommand):
    help = "Seed mock data: users, customers, addresses"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Xóa dữ liệu cũ trước khi seed")

    def handle(self, *args, **options):
        if options.get("clear"):
            WebAddress.objects.all().delete()
            Customer.objects.all().delete()
            User.objects.all().delete()
            self.stdout.write(self.style.WARNING("Đã xóa dữ liệu cũ."))

        if User.objects.exists():
            self.stdout.write(self.style.NOTICE("Đã có dữ liệu User/Customer, bỏ qua seed."))
            return

        users_data = [
            {"username": "customer1", "email": "customer1@example.com", "phone": "0901111111"},
            {"username": "customer2", "email": "customer2@example.com", "phone": "0902222222"},
            {"username": "customer3", "email": "customer3@example.com", "phone": "0903333333"},
        ]
        password = make_password("password123")
        for u in users_data:
            u["password"] = password
            u["is_active"] = True

        created = []
        for u in users_data:
            user = User.objects.create(**u)
            customer = Customer.objects.create(user=user, loyalty_points=0)
            WebAddress.objects.create(
                customer=customer,
                recipient_name=user.username,
                address_line="123 Đường ABC",
                city="TP.HCM",
                state="",
                country="Vietnam",
                postal_code="700000",
                phone=user.phone or "",
                is_default=True,
            )
            created.append(user.username)

        self.stdout.write(self.style.SUCCESS(f"Created users & customers: {', '.join(created)}"))
