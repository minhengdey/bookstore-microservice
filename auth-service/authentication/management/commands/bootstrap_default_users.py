import os
import time

from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction

from authentication.exceptions import UpstreamServiceError
from authentication.models import AuthUser
from authentication.services import AuthService


def _build_default_users():
    admin_username = os.environ.get("DEFAULT_ADMIN_USERNAME", "admin").strip()
    admin_email = os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@ecommerce.local").strip().lower()
    admin_password = os.environ.get("DEFAULT_ADMIN_PASSWORD", "Admin@12345")
    customer_password = os.environ.get("DEFAULT_CUSTOMER_PASSWORD", "password123")
    staff_password = os.environ.get("DEFAULT_STAFF_PASSWORD", "password123")
    customer_count = max(3, int(os.environ.get("MOCK_CUSTOMER_COUNT", "50")))

    users = [
        {
            "username": admin_username,
            "email": admin_email,
            "password": admin_password,
            "roles": ["ADMIN"],
            "full_name": "System Admin",
            "phone": "0000000000",
            "department": "IT",
            "position": "Administrator",
            "storage_code": "HQ",
        },
        {
            "username": "customer1",
            "email": "customer1@ecommerce.local",
            "password": customer_password,
            "roles": ["CUSTOMER"],
            "full_name": "Khách hàng 1",
            "phone": "0901111111",
        },
        {
            "username": "customer2",
            "email": "customer2@ecommerce.local",
            "password": customer_password,
            "roles": ["CUSTOMER"],
            "full_name": "Khách hàng 2",
            "phone": "0902222222",
        },
        {
            "username": "customer3",
            "email": "customer3@ecommerce.local",
            "password": customer_password,
            "roles": ["CUSTOMER"],
            "full_name": "Khách hàng 3",
            "phone": "0903333333",
        },
        {
            "username": "staff1",
            "email": "staff1@ecommerce.local",
            "password": staff_password,
            "roles": ["STAFF"],
            "full_name": "Nhân viên 1",
            "phone": "0911111111",
            "department": "Vận hành",
            "position": "Nhân viên kho",
            "storage_code": "WH-01",
        },
        {
            "username": "staff2",
            "email": "staff2@ecommerce.local",
            "password": staff_password,
            "roles": ["STAFF"],
            "full_name": "Nhân viên 2",
            "phone": "0922222222",
            "department": "Vận hành",
            "position": "Nhân viên kho",
            "storage_code": "WH-02",
        },
        {
            "username": "manager1",
            "email": "manager1@ecommerce.local",
            "password": staff_password,
            "roles": ["STAFF"],
            "full_name": "Quản lý 1",
            "phone": "0933333333",
            "department": "Vận hành",
            "position": "Quản lý",
            "storage_code": "WH-MGR",
        },
    ]

    for i in range(4, customer_count + 1):
        users.append({
            "username": f"customer{i}",
            "email": f"customer{i}@ecommerce.local",
            "password": customer_password,
            "roles": ["CUSTOMER"],
            "full_name": f"Khách hàng {i}",
            "phone": f"09{10000000 + i:08d}"[-10:],
        })

    return users


class Command(BaseCommand):
    help = "Create or refresh default demo accounts for each role (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-input",
            action="store_true",
            help="Do not prompt for input.",
        )

    def handle(self, *args, **options):
        auth_service = AuthService()
        self._wait_for_user_service(auth_service)

        created_count = 0
        refreshed_count = 0
        profile_count = 0

        for spec in _build_default_users():
            created, profile_created = self._ensure_user(auth_service, spec)
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created account: {spec['username']}"))
            else:
                refreshed_count += 1
                self.stdout.write(self.style.SUCCESS(f"Refreshed account: {spec['username']}"))
            if profile_created:
                profile_count += 1
                self.stdout.write(self.style.SUCCESS(f"  + profile for {spec['username']}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Default users ready ({created_count} created, {refreshed_count} refreshed, {profile_count} profiles added)."
            )
        )

    def _wait_for_user_service(self, auth_service: AuthService, max_attempts: int = 60) -> None:
        probe_id = "00000000-0000-0000-0000-000000000000"
        for attempt in range(1, max_attempts + 1):
            try:
                auth_service.user_client.get(f"/internal/users/{probe_id}/")
                return
            except UpstreamServiceError as exc:
                if exc.status_code == 404:
                    return
            except Exception:
                pass
            self.stdout.write(f"Waiting for user-service ({attempt}/{max_attempts})...")
            time.sleep(2)

        self.stdout.write(self.style.WARNING("user-service not reachable; continuing anyway."))

    def _ensure_user(self, auth_service: AuthService, spec: dict) -> tuple[bool, bool]:
        roles = [r.upper() for r in spec["roles"]]
        is_admin = any(r in ("ADMIN", "SUPER_ADMIN") for r in roles)
        is_staff = is_admin or "STAFF" in roles

        with transaction.atomic():
            try:
                user, created = AuthUser.objects.get_or_create(
                    username=spec["username"],
                    defaults={
                        "email": spec["email"],
                        "is_staff": is_staff,
                        "is_superuser": is_admin,
                        "is_active": True,
                    },
                )
            except IntegrityError:
                user = AuthUser.objects.get(username=spec["username"])
                created = False

            user.email = spec["email"]
            user.is_staff = is_staff
            user.is_superuser = is_admin
            user.is_active = True
            user.set_password(spec["password"])
            user.save(update_fields=["email", "is_staff", "is_superuser", "is_active", "password"])

        profile_created = False
        try:
            auth_service.user_client.get(f"/internal/users/{user.id}/")
        except UpstreamServiceError as exc:
            if exc.status_code != 404:
                raise
            payload = {
                "auth_user_id": str(user.id),
                "full_name": spec.get("full_name", spec["username"]),
                "phone": spec.get("phone", ""),
                "roles": roles,
                "storage_code": spec.get("storage_code", ""),
                "department": spec.get("department", ""),
                "position": spec.get("position", ""),
            }
            auth_service.user_client.post("/internal/users/", payload)
            profile_created = True

        return created, profile_created
