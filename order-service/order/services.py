import logging
from decimal import Decimal
from django.db import transaction
from .models import Order, OrderItem, Discount, OrderDiscount, Invoice, OrderStatus
from common.client import InternalClient

logger = logging.getLogger(__name__)

PRODUCT_SERVICE_URL = "http://product-service:8000"
PAY_SERVICE_URL = "http://payment-service:8000"

class OrderService:
    def __init__(self):
        self.client = InternalClient()

    def list_orders(self, customer_id=None):
        if customer_id:
            return Order.objects.filter(customer_id=customer_id).prefetch_related('items', 'order_discounts')
        return Order.objects.all().prefetch_related('items', 'order_discounts')

    def get_order(self, order_id):
        order = Order.objects.prefetch_related('items', 'order_discounts', 'invoice').filter(pk=order_id).first()
        if not order:
            raise ValueError(f"Order {order_id} not found")
        return order

    def _create_order_db(self, data: dict):
        items_data = data.pop("items", [])
        discount_code = data.pop("discount_code", None)
        
        order = Order.objects.create(status=OrderStatus.PENDING_PAYMENT, **data)
        
        total = Decimal("0")
        for item in items_data:
            product_price = self._get_product_price(item["product_id"])
            unit_price = Decimal(str(item.get("unit_price", product_price)))
            quantity = int(item["quantity"])
            discount_val = Decimal(str(item.get("discount", 0)))
            
            OrderItem.objects.create(
                order=order, product_id=item["product_id"],
                quantity=quantity, unit_price=unit_price,
                discount=discount_val
            )
            total += unit_price * quantity
            
        discount_amount = Decimal("0")
        if discount_code:
            discount = Discount.objects.filter(discount_code=discount_code, is_active=True).first()
            if discount:
                if discount.is_percentage:
                    discount_amount = total * discount.discount_value / Decimal("100")
                else:
                    discount_amount = discount.discount_value
                OrderDiscount.objects.create(order=order, discount_id=discount.id, applied_value=discount_amount)
                
        shipping_fee = Decimal(str(data.get("shipping_fee", 0)))
        final_total = total - discount_amount + shipping_fee
        order.total_amount = final_total
        order.discount_amount = discount_amount
        order.save(update_fields=["total_amount", "discount_amount"])
        
        Invoice.objects.create(order=order, admin_id=order.admin_id)
        return order

    def create_order(self, data: dict):
        items = [{"product_id": item["product_id"], "quantity": item["quantity"]} for item in data.get("items", [])]
        if not items:
            raise ValueError("Order must contain items")
            
        try:
            with transaction.atomic():
                order = self._create_order_db(data)
                
                # Reserve stock synchronously WITH order_id
                r = self.client.post(f"{PRODUCT_SERVICE_URL}/internal/reserve-stock/", json={"order_id": order.id, "items": items})
                if r.status_code not in (200, 201):
                    err = r.json().get("error", "Stock reservation failed")
                    raise ValueError(err)
                    
                # Write to Outbox instead of calling payment-service synchronously
                from .models import OrderOutbox
                outbox_payload = {
                    "order_id": order.id,
                    "customer_id": order.customer_id,
                    "total_amount": str(order.total_amount),
                    "items": items
                }
                OrderOutbox.objects.create(
                    aggregate_id=str(order.id),
                    event_type="order_created",
                    payload=outbox_payload
                )
        except Exception as e:
            raise ValueError(f"Order creation failed: {e}")
            
        return order

    def cancel_order(self, order_id):
        order = self.get_order(order_id)
        if order.status not in (OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PENDING_PAYMENT):
            raise ValueError(f"Cannot cancel order in status: {order.status}")
        order.status = OrderStatus.CANCELLED
        order.save(update_fields=["status"])
        
        items = [{"product_id": item.product_id, "quantity": item.quantity} for item in order.items.all()]
        self._release_stock(order.id, items)
        return order

    def _release_stock(self, order_id: int, items: list):
        try:
            r = self.client.post(f"{PRODUCT_SERVICE_URL}/internal/release-stock/", json={"order_id": order_id, "items": items})
            if r.status_code not in (200, 201):
                logger.error(f"Failed to release stock: {r.text}")
        except Exception as e:
            logger.error(f"Failed to communicate with product-service for stock release: {e}")

    def update_status(self, order_id, new_status):
        order = self.get_order(order_id)
        order.status = new_status
        order.save(update_fields=["status"])
        return order

    def _get_product_price(self, product_id) -> float:
        try:
            r = self.client.get(f"{PRODUCT_SERVICE_URL}/internal/products/{product_id}/")
            if r.status_code == 200:
                return float(r.json().get("price", 0))
        except Exception as e:
            logger.warning(f"product-service unreachable: {e}")
        return 0.0


class DiscountService:
    def list(self): return Discount.objects.all()
    def get(self, pk):
        d = Discount.objects.filter(pk=pk).first()
        if not d: raise ValueError(f"Discount {pk} not found")
        return d
    def create(self, data): return Discount.objects.create(**data)
    def update(self, pk, data):
        d = self.get(pk)
        for k, v in data.items(): setattr(d, k, v)
        d.save()
        return d
