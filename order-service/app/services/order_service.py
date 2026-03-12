import requests, logging
from decimal import Decimal
from app.repositories import OrderRepository, DiscountRepository

logger = logging.getLogger(__name__)

BOOK_SERVICE_URL = "http://book-service:8000"
PAY_SERVICE_URL = "http://pay-service:8000"
SHIP_SERVICE_URL = "http://ship-service:8000"


class OrderService:
    def __init__(self):
        self.repo = OrderRepository()
        self.discount_repo = DiscountRepository()

    def list_orders(self, customer_id=None):
        if customer_id:
            return self.repo.get_by_customer(customer_id)
        return self.repo.get_all()

    def get_order(self, order_id):
        order = self.repo.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        return order

    def create_order(self, data: dict):
        items_data = data.pop("items", [])
        discount_code = data.pop("discount_code", None)

        order = self.repo.create(**data)

        total = Decimal("0")
        for item in items_data:
            book_price = self._get_book_price(item["book_id"])
            unit_price = item.get("unit_price", book_price)
            self.repo.add_item(order, book_id=item["book_id"],
                               quantity=item["quantity"], unit_price=unit_price,
                               discount=item.get("discount", 0))
            total += Decimal(str(unit_price)) * item["quantity"]

        discount_amount = Decimal("0")
        if discount_code:
            discount = self.discount_repo.get_by_code(discount_code)
            if discount:
                if discount.is_percentage:
                    discount_amount = total * discount.discount_value / 100
                else:
                    discount_amount = discount.discount_value
                self.repo.apply_discount(order, discount.id, discount_amount)

        shipping_fee = Decimal(str(data.get("shipping_fee", 0)))
        final_total = total - discount_amount + shipping_fee
        order = self.repo.update_total(order, final_total)
        order.discount_amount = discount_amount
        order.save(update_fields=["discount_amount"])

        self.repo.create_invoice(order)
        return self.repo.get_by_id(order.id)

    def cancel_order(self, order_id):
        order = self.get_order(order_id)
        if order.status not in ("pending", "confirmed"):
            raise ValueError(f"Cannot cancel order in status: {order.status}")
        return self.repo.update_status(order, "cancelled")

    def update_status(self, order_id, new_status):
        order = self.get_order(order_id)
        return self.repo.update_status(order, new_status)

    def _get_book_price(self, book_id) -> float:
        try:
            r = requests.get(f"{BOOK_SERVICE_URL}/books/{book_id}/", timeout=5)
            if r.status_code == 200:
                return float(r.json().get("sale_price", 0))
        except requests.exceptions.RequestException as e:
            logger.warning(f"book-service unreachable: {e}")
        return 0.0


class DiscountService:
    def __init__(self): self.repo = DiscountRepository()
    def list(self): return self.repo.get_all()
    def get(self, pk):
        d = self.repo.get_by_id(pk)
        if not d: raise ValueError(f"Discount {pk} not found")
        return d
    def create(self, data): return self.repo.create(**data)
    def update(self, pk, data): return self.repo.update(self.get(pk), **data)
