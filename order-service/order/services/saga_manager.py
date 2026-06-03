import uuid
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import logging

from order.models import Order, OrderItem, OrderSaga, OrderStatusHistory, OutboxEvent
from order.services.catalog_client import CatalogClient
from order.services.payment_client import PaymentClient
from order.services.cart_service import CartService

logger = logging.getLogger(__name__)

class PriceChangedError(Exception):
    pass

class OrderSagaManager:
    @staticmethod
    @transaction.atomic
    def start_checkout(user_id: str, cart_items: list, shipping_address: dict) -> Order:
        # 1. Fetch exact prices from Catalog to prevent stale cart prices
        total_amount = Decimal('0.0')
        order_items_data = []
        
        for item in cart_items:
            variant_id = item['variant_id']
            qty = item['quantity']
            variant_data = CatalogClient.get_variant(variant_id)
            
            if not variant_data:
                raise ValueError(f"Variant {variant_id} does not exist")
                
            current_price = Decimal(str(variant_data['price']))
            total_amount += current_price * qty
            
            order_items_data.append({
                'product_id': variant_data['product_id'],
                'variant_id': variant_id,
                'quantity': qty,
                'unit_price': current_price,
                'product_name': variant_data.get('product_name', 'Unknown Product'),
                'variant_sku': variant_data.get('sku', 'Unknown SKU'),
                'variant_attributes': variant_data.get('attributes', {})
            })

        order = Order.objects.create(
            user_id=user_id,
            status='RESERVING_STOCK',
            total_amount=total_amount,
            final_amount=total_amount, # No promotions for now
            shipping_address=shipping_address
        )
        
        for item_data in order_items_data:
            OrderItem.objects.create(order=order, **item_data)
            
        saga = OrderSaga.objects.create(
            order=order,
            correlation_id=order.correlation_id,
            current_step='INVENTORY_RESERVE',
            status='PENDING'
        )
        
        OrderStatusHistory.objects.create(order=order, status='RESERVING_STOCK', reason='Checkout started')

        # Publish event for inventory service
        inventory_items = [{"variant_id": str(i['variant_id']), "quantity": i['quantity']} for i in order_items_data]
        OutboxEvent.objects.create(
            aggregate_id=order.id,
            aggregate_type='Order',
            event_type='order.checkout.started',
            message_id=uuid.uuid4(),
            payload={
                "event_version": "v1",
                "order_id": str(order.id),
                "correlation_id": str(order.correlation_id),
                "items": inventory_items
            }
        )
        
        # Clear cart
        CartService().clear_cart(user_id)
        
        return order

    @staticmethod
    @transaction.atomic
    def handle_inventory_reserved(order_id: str):
        try:
            order = Order.objects.select_for_update().get(id=order_id)
            if order.status != 'RESERVING_STOCK':
                return
                
            order.status = 'STOCK_RESERVED'
            order.save()
            OrderStatusHistory.objects.create(order=order, status='STOCK_RESERVED', reason='Inventory reserved')
            
            saga = order.saga
            saga.current_step = 'PAYMENT_CREATE'
            saga.timeout_at = timezone.now() + timedelta(minutes=15)
            saga.save()
            
            # Sync call to payment service
            try:
                payment_data = PaymentClient.create_payment_session(str(order.id), float(order.final_amount))
                order.payment_id = payment_data.get('payment_id')
                order.payment_provider = payment_data.get('provider', 'STRIPE')
                order.status = 'PAYMENT_PROCESSING'
                order.save()
                
                OrderStatusHistory.objects.create(order=order, status='PAYMENT_PROCESSING', reason='Payment intent created')
                
            except Exception as e:
                # Synchronous failure, we must trigger rollback
                logger.error(f"Failed to create payment for order {order.id}: {str(e)}")
                order.status = 'PAYMENT_FAILED'
                order.save()
                saga.status = 'FAILED'
                saga.last_error = str(e)
                saga.save()
                OrderSagaManager.trigger_rollback(order.id, 'Payment API Error')
                
        except Order.DoesNotExist:
            pass

    @staticmethod
    @transaction.atomic
    def handle_inventory_reservation_failed(order_id: str, reason: str):
        try:
            order = Order.objects.select_for_update().get(id=order_id)
            order.status = 'CANCELLING'
            order.save()
            
            saga = order.saga
            saga.status = 'FAILED'
            saga.last_error = reason
            saga.save()
            
            OrderSagaManager.trigger_cancel(order.id, f"Reservation failed: {reason}")
        except Order.DoesNotExist:
            pass

    @staticmethod
    @transaction.atomic
    def handle_payment_succeeded(order_id: str):
        try:
            order = Order.objects.select_for_update().get(id=order_id)
            if order.status != 'PAYMENT_PROCESSING':
                return
                
            order.status = 'WAITING_INVENTORY_CONFIRM'
            order.save()
            OrderStatusHistory.objects.create(order=order, status='WAITING_INVENTORY_CONFIRM', reason='Payment succeeded')
            
            saga = order.saga
            saga.current_step = 'INVENTORY_CONFIRM'
            saga.save()
            
            OutboxEvent.objects.create(
                aggregate_id=order.id,
                aggregate_type='Order',
                event_type='inventory.stock.confirm.requested',
                message_id=uuid.uuid4(),
                payload={
                    "event_version": "v1",
                    "order_id": str(order.id),
                    "correlation_id": str(order.correlation_id)
                }
            )
        except Order.DoesNotExist:
            pass

    @staticmethod
    @transaction.atomic
    def handle_payment_failed(order_id: str, reason: str):
        try:
            order = Order.objects.select_for_update().get(id=order_id)
            order.status = 'PAYMENT_FAILED'
            order.save()
            
            saga = order.saga
            saga.status = 'FAILED'
            saga.last_error = reason
            saga.save()
            
            OrderSagaManager.trigger_rollback(order.id, reason)
        except Order.DoesNotExist:
            pass

    @staticmethod
    @transaction.atomic
    def handle_inventory_confirmed(order_id: str):
        try:
            order = Order.objects.select_for_update().get(id=order_id)
            if order.status != 'WAITING_INVENTORY_CONFIRM':
                return
                
            order.status = 'COMPLETED'
            order.save()
            OrderStatusHistory.objects.create(order=order, status='COMPLETED', reason='Inventory officially confirmed')
            
            saga = order.saga
            saga.status = 'SUCCESS'
            saga.save()
            
        except Order.DoesNotExist:
            pass

    @staticmethod
    def trigger_rollback(order_id: str, reason: str):
        order = Order.objects.get(id=order_id)
        OrderStatusHistory.objects.create(order=order, status='CANCELLING', reason=f"Rolling back: {reason}")
        
        OutboxEvent.objects.create(
            aggregate_id=order.id,
            aggregate_type='Order',
            event_type='inventory.stock.release.requested',
            message_id=uuid.uuid4(),
            payload={
                "event_version": "v1",
                "order_id": str(order.id),
                "correlation_id": str(order.correlation_id),
                "reason": "PAYMENT_FAILED"
            }
        )
        OrderSagaManager.trigger_cancel(order_id, reason)

    @staticmethod
    def trigger_cancel(order_id: str, reason: str):
        order = Order.objects.get(id=order_id)
        order.status = 'CANCELLED'
        order.save()
        OrderStatusHistory.objects.create(order=order, status='CANCELLED', reason=reason)
