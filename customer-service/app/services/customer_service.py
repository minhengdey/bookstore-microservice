import requests
import logging
from app.repositories import CustomerRepository, UserRepository, WebAddressRepository

logger = logging.getLogger(__name__)

CART_SERVICE_URL = "http://cart-service:8000"


class CustomerService:
    def __init__(self):
        self.customer_repo = CustomerRepository()
        self.user_repo = UserRepository()
        self.address_repo = WebAddressRepository()

    # ── User operations ──────────────────────────────────────────────────────

    def list_customers(self):
        return self.customer_repo.get_all()

    def get_customer(self, customer_id: int):
        customer = self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        return customer

    def register_customer(self, user_data: dict, customer_data: dict = None):
        """Create User + Customer and automatically provision a Cart."""
        if self.user_repo.get_by_email(user_data.get("email", "")):
            raise ValueError("Email already registered")
        if self.user_repo.get_by_username(user_data.get("username", "")):
            raise ValueError("Username already taken")

        from django.contrib.auth.hashers import make_password
        raw_password = user_data.pop("password", "")
        user_data["password"] = make_password(raw_password)

        user = self.user_repo.create(**user_data)
        extra = customer_data or {}
        customer = self.customer_repo.create(user=user, **extra)

        self._create_cart_for_customer(customer.id)
        return customer

    def update_customer(self, customer_id: int, data: dict):
        customer = self.get_customer(customer_id)
        user_fields = {k: v for k, v in data.items() if hasattr(customer.user, k)}
        customer_fields = {k: v for k, v in data.items() if k in ("loyalty_points",)}
        if user_fields:
            self.user_repo.update(customer.user, **user_fields)
        if customer_fields:
            self.customer_repo.update(customer, **customer_fields)
        customer.refresh_from_db()
        return customer

    def delete_customer(self, customer_id: int):
        customer = self.get_customer(customer_id)
        self.customer_repo.delete(customer)

    # ── Address operations ───────────────────────────────────────────────────

    def list_addresses(self, customer_id: int):
        customer = self.get_customer(customer_id)
        return self.address_repo.get_by_customer(customer)

    def add_address(self, customer_id: int, address_data: dict):
        customer = self.get_customer(customer_id)
        address = self.address_repo.create(customer=customer, **address_data)
        if address_data.get("is_default"):
            self.address_repo.set_default(customer, address)
        return address

    def update_address(self, address_id: int, address_data: dict):
        address = self.address_repo.get_by_id(address_id)
        if not address:
            raise ValueError(f"Address {address_id} not found")
        return self.address_repo.update(address, **address_data)

    def delete_address(self, address_id: int):
        address = self.address_repo.get_by_id(address_id)
        if not address:
            raise ValueError(f"Address {address_id} not found")
        self.address_repo.delete(address)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _create_cart_for_customer(self, customer_id: int):
        try:
            requests.post(
                f"{CART_SERVICE_URL}/carts/",
                json={"customer_id": customer_id},
                timeout=5,
            )
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not reach cart-service: {e}")
