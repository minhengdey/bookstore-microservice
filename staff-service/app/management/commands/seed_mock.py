"""
Tạo dữ liệu mẫu: User (staff_users), InventoryStaff.
Chạy: python manage.py seed_mock
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from app.models import User, InventoryStaff


class Command(BaseCommand):
    help = "Seed mock data: staff users and inventory staff"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Xóa dữ liệu cũ trước khi seed")

    def handle(self, *args, **options):
        if options.get("clear"):
            InventoryStaff.objects.all().delete()
            User.objects.all().delete()
            self.stdout.write(self.style.WARNING("Đã xóa dữ liệu staff."))

        if User.objects.filter(username="staff1").exists():
            self.stdout.write(self.style.NOTICE("Đã có dữ liệu staff, bỏ qua seed."))
            return

        pw = make_password("password123")
        users = [
            {"username": "staff1", "email": "staff1@bookstore.com", "password": pw, "phone": "0911111111"},
            {"username": "staff2", "email": "staff2@bookstore.com", "password": pw, "phone": "0922222222"},
            {"username": "manager1", "email": "manager1@bookstore.com", "password": pw, "phone": "0933333333"},
        ]
        roles = [InventoryStaff.ROLE_STAFF, InventoryStaff.ROLE_STAFF, InventoryStaff.ROLE_MANAGER]
        for i, u in enumerate(users):
            user = User.objects.create(**u)
            InventoryStaff.objects.create(
                user=user,
                storage_code=f"STF{i+1:03d}",
                department="Kho",
                position="Nhân viên kho" if roles[i] == "staff" else "Quản lý",
                role=roles[i],
            )

        self.stdout.write(self.style.SUCCESS("Created 2 staff + 1 manager (staff1, staff2, manager1 / password123)."))
