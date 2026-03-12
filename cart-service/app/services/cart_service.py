import requests
import logging
from app.repositories import CartRepository

logger = logging.getLogger(__name__)

BOOK_SERVICE_URL = "http://book-service:8000"


class CartService:
    def __init__(self):
        self.repo = CartRepository()

    def create_cart(self, customer_id: int):
        _, created = self.repo.get_or_create_cart(customer_id)
        return self.repo.get_by_customer(customer_id)

    def get_cart(self, customer_id: int):
        cart = self.repo.get_by_customer(customer_id)
        if not cart:
            raise ValueError(f"Cart not found for customer {customer_id}")
        return cart

    def add_item(self, customer_id: int, book_id: int, quantity: int):
        # Validate book existence + get price from book-service
        book_data = self._fetch_book(book_id)
        if not book_data:
            raise ValueError(f"Book {book_id} not found")

        unit_price = float(book_data.get("sale_price", 0))
        cart = self.repo.get_by_customer(customer_id)
        if not cart:
            raise ValueError(f"Cart not found for customer {customer_id}")

        return self.repo.add_item(cart, book_id, quantity, unit_price)

    def update_item(self, customer_id: int, item_id: int, quantity: int):
        cart = self.get_cart(customer_id)
        item = self.repo.get_item_by_id(item_id)
        if not item or item.cart_id != cart.id:
            raise ValueError(f"Cart item {item_id} not found")
        if quantity <= 0:
            self.repo.remove_item(item)
            return None
        return self.repo.update_item_quantity(item, quantity)

    def remove_item(self, customer_id: int, item_id: int):
        cart = self.get_cart(customer_id)
        item = self.repo.get_item_by_id(item_id)
        if not item or item.cart_id != cart.id:
            raise ValueError(f"Cart item {item_id} not found")
        self.repo.remove_item(item)

    def clear_cart(self, customer_id: int):
        cart = self.get_cart(customer_id)
        self.repo.clear_cart(cart)

    def _fetch_book(self, book_id: int) -> dict | None:
        try:
            r = requests.get(f"{BOOK_SERVICE_URL}/books/{book_id}/", timeout=5)
            if r.status_code == 200:
                return r.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"book-service unreachable: {e}")
        return None
