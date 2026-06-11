import logging
from decimal import Decimal
from django.db import transaction
from .legacy_models import LegacyOrder as Order, LegacyOrderItem as OrderItem, LegacyDiscount as Discount, LegacyOrderDiscount as OrderDiscount, LegacyInvoice as Invoice, OrderStatus
from common.client import InternalClient

logger = logging.getLogger(__name__)

PRODUCT_SERVICE_URL = "http://product-service:8000"
PAY_SERVICE_URL = "http://payment-service:8000"
PROMOTION_SERVICE_URL = "http://promotion-service:8000"

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
        promotion_code = data.pop("promotion_code", None)
        discount_code = data.pop("discount_code", None)
        shipping_address = data.pop("shipping_address", None)
        address_id = data.pop("address_id", None)
        shipping_method_id = data.pop("shipping_method_id", None)
        
        if promotion_code:
            data["voucher_code"] = promotion_code
        if shipping_address:
            snapshot = dict(shipping_address) if isinstance(shipping_address, dict) else shipping_address
            if shipping_method_id:
                snapshot["shipping_method_id"] = shipping_method_id
            data["shipping_address_snapshot"] = snapshot
        elif shipping_method_id:
            data["shipping_address_snapshot"] = {"shipping_method_id": shipping_method_id}
        if address_id:
            data["address_id"] = address_id
            
        order = Order.objects.create(status=OrderStatus.PENDING_PAYMENT, **data)
        
        total = Decimal("0")
        for item in items_data:
            unit_price = Decimal(str(item.get("unit_price", 0)))
            quantity = int(item["quantity"])
            discount_val = Decimal(str(item.get("discount", 0)))
            variant_id = item.get("variant_id")
            product_name = item.get("product_name") or ""
            variant_name = item.get("variant_name") or ""
            if not product_name:
                snapshot = self._get_product_snapshot(item["product_id"], variant_id)
                product_name = snapshot.get("product_name") or f"Sản phẩm #{item['product_id']}"
                variant_name = variant_name or snapshot.get("variant_name") or ""

            OrderItem.objects.create(
                order=order, product_id=item["product_id"],
                variant_id=variant_id,
                product_name=product_name,
                variant_name=variant_name,
                quantity=quantity, unit_price=unit_price,
                discount=discount_val
            )
            total += unit_price * quantity
            
        discount_amount = Decimal("0")
        if promotion_code:
            try:
                r = self.client.post(
                    f"{PROMOTION_SERVICE_URL}/api/promotions/apply-voucher/",
                    json={"code": promotion_code, "order_amount": float(total)},
                )
                if r.status_code == 200:
                    discount_amount = Decimal(str(r.json().get("discount_amount", 0)))
            except Exception as e:
                logger.error(f"Failed to apply voucher via promotion-service: {e}")
        elif discount_code:
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
        items = [{"product_id": item["product_id"], "variant_id": item.get("variant_id"), "quantity": item["quantity"]} for item in data.get("items", [])]
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
                from .legacy_models import LegacyOrderOutbox as OrderOutbox
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

    def request_return(self, order_id, customer_id=None):
        order = self.get_order(order_id)
        if customer_id is not None and int(order.customer_id) != int(customer_id):
            raise ValueError("Order does not belong to this customer")
        if order.status not in (OrderStatus.DELIVERED, OrderStatus.SHIPPING):
            raise ValueError(f"Cannot request return for order in status: {order.status}")
        return self.update_status(order_id, OrderStatus.RETURN_REQUESTED)

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
        
        # State Machine Transition Validation
        valid_transitions = {
            OrderStatus.PENDING_PAYMENT: [OrderStatus.PAID, OrderStatus.CANCELLED],
            OrderStatus.PAID: [OrderStatus.PROCESSING, OrderStatus.REFUNDED],
            OrderStatus.PROCESSING: [OrderStatus.SHIPPING, OrderStatus.CANCELLED],
            OrderStatus.SHIPPING: [OrderStatus.DELIVERED, OrderStatus.RETURN_REQUESTED],
            OrderStatus.DELIVERED: [OrderStatus.RETURN_REQUESTED],
            OrderStatus.RETURN_REQUESTED: [OrderStatus.RETURNED],
            OrderStatus.RETURNED: [OrderStatus.REFUNDED],
            OrderStatus.CANCELLED: [],
            OrderStatus.REFUNDED: []
        }
        
        if new_status not in valid_transitions.get(order.status, []):
            if order.status == new_status:
                pass # Same status, do nothing
            else:
                raise ValueError(f"Invalid state transition from {order.status} to {new_status}")
                
        order.status = new_status
        order.save(update_fields=["status"])
        
        # Gọi shipping-service nếu trạng thái liên quan đến giao hàng
        if new_status in [OrderStatus.SHIPPING, OrderStatus.DELIVERED]:
            try:
                # Gửi thông tin sang shipping-service
                shipping_payload = {
                    "order_id": order.id,
                    "status": "in_transit" if new_status == OrderStatus.SHIPPING else "delivered"
                }
                SHIPPING_SERVICE_URL = "http://shipping-service:8000"
                # TODO: Thực tế cần thêm retry / async ở đây để đảm bảo tính ổn định
                self.client.post(f"{SHIPPING_SERVICE_URL}/internal/shipping/status/", json=shipping_payload)
            except Exception as e:
                logger.error(f"Failed to sync status with shipping-service: {e}")
                
        return order

    def bulk_update_status(self, order_ids, action=None, new_status=None):
        """Cập nhật trạng thái nhiều đơn hàng (duyệt/hủy loạt)."""
        if not order_ids:
            raise ValueError("order_ids is required")

        approve_map = {
            OrderStatus.PENDING_PAYMENT: OrderStatus.PAID,
            OrderStatus.PAID: OrderStatus.PROCESSING,
            OrderStatus.PROCESSING: OrderStatus.SHIPPING,
        }

        updated, failed = [], []
        for order_id in order_ids:
            try:
                order = self.get_order(order_id)
                if action == "approve":
                    target = approve_map.get(order.status)
                    if not target:
                        raise ValueError(f"Cannot approve order in status: {order.status}")
                elif action == "cancel":
                    if order.status in (OrderStatus.CANCELLED, OrderStatus.REFUNDED, OrderStatus.DELIVERED):
                        raise ValueError(f"Cannot cancel order in status: {order.status}")
                    target = OrderStatus.CANCELLED
                elif new_status:
                    target = new_status
                else:
                    raise ValueError("Must provide action or status")

                self.update_status(order_id, target)
                updated.append(order_id)
            except ValueError as e:
                failed.append({"order_id": order_id, "error": str(e)})

        return {"updated": updated, "failed": failed, "total": len(order_ids)}

    def _get_product_snapshot(self, product_id, variant_id=None) -> dict:
        try:
            r = self.client.get(f"{PRODUCT_SERVICE_URL}/products/{product_id}/")
            if r.status_code == 200:
                data = r.json()
                name = data.get("name") or ""
                variant_name = ""
                if variant_id:
                    for v in data.get("variants", []):
                        if v.get("id") == variant_id:
                            parts = [p for p in (v.get("color"), v.get("size")) if p]
                            variant_name = " - ".join(parts)
                            if variant_name:
                                name = f"{name} ({variant_name})"
                            break
                return {"product_name": name, "variant_name": variant_name}
        except Exception as e:
            logger.warning(f"product-service unreachable: {e}")
        return {}

    def _get_product_price(self, product_id) -> float:
        try:
            r = self.client.get(f"{PRODUCT_SERVICE_URL}/products/{product_id}/")
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
