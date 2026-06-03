import uuid
from django.db import transaction, connection
from django.utils import timezone
from datetime import timedelta
import os

from inventory.models import (
    Inventory, InventoryMovement, ReservationBatch, 
    StockReservation, OutboxEvent, ProcessedMessage
)

class OutOfStockError(Exception):
    pass

class ConcurrentUpdateError(Exception):
    pass

class InventoryService:
    @staticmethod
    def get_ttl_minutes():
        return int(os.environ.get('RESERVATION_TTL_MINUTES', '15'))

    @staticmethod
    @transaction.atomic
    def initialize_stock(variant_id: str):
        inventory, created = Inventory.objects.get_or_create(
            variant_id=variant_id,
            defaults={
                'total_stock': 0,
                'available_stock': 0,
                'reserved_stock': 0,
                'version': 0,
                'is_active': True
            }
        )
        return inventory

    @staticmethod
    @transaction.atomic
    def reserve_stock(order_id: str, items: list, correlation_id: str = None, idempotency_key: str = None):
        if idempotency_key:
            if ProcessedMessage.objects.filter(message_id=idempotency_key).exists():
                return  # Idempotent skip
            ProcessedMessage.objects.create(message_id=idempotency_key)

        expires_at = timezone.now() + timedelta(minutes=InventoryService.get_ttl_minutes())
        batch = ReservationBatch.objects.create(
            order_id=order_id,
            correlation_id=correlation_id,
            status='PENDING',
            expires_at=expires_at
        )

        for item in items:
            variant_id = item['variant_id']
            quantity = item['quantity']

            # Explicit RAW SQL for Optimistic Locking
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE inventory_inventory 
                    SET available_stock = available_stock - %s,
                        reserved_stock = reserved_stock + %s,
                        version = version + 1,
                        updated_at = %s
                    WHERE variant_id = %s AND available_stock >= %s
                    RETURNING total_stock, available_stock, reserved_stock
                    """,
                    [quantity, quantity, timezone.now(), variant_id, quantity]
                )
                row = cursor.fetchone()

                if not row:
                    # Determine why it failed
                    try:
                        current_inv = Inventory.objects.get(variant_id=variant_id)
                        if current_inv.available_stock < quantity:
                            raise OutOfStockError(f"Variant {variant_id} is out of stock.")
                        else:
                            raise ConcurrentUpdateError(f"Concurrent update on variant {variant_id}.")
                    except Inventory.DoesNotExist:
                        raise OutOfStockError(f"Variant {variant_id} does not exist.")

                total_stock, available_stock, reserved_stock = row

            StockReservation.objects.create(
                batch=batch,
                variant_id=variant_id,
                quantity=quantity,
                status='PENDING',
                expires_at=expires_at
            )

            # Create Inventory Movement
            InventoryMovement.objects.create(
                variant_id=variant_id,
                type='RESERVE',
                quantity=quantity,
                available_before=available_stock + quantity,
                available_after=available_stock,
                reserved_before=reserved_stock - quantity,
                reserved_after=reserved_stock,
                total_before=total_stock,
                total_after=total_stock,
                reference_id=batch.batch_id
            )

        # Publish Event
        OutboxEvent.objects.create(
            aggregate_id=batch.batch_id,
            aggregate_type='ReservationBatch',
            event_type='inventory.stock.reserved',
            message_id=uuid.uuid4(),
            payload={
                "event_version": "v1",
                "order_id": str(order_id),
                "correlation_id": str(correlation_id),
                "items": items
            }
        )
        return batch

    @staticmethod
    @transaction.atomic
    def confirm_reservation(order_id: str, idempotency_key: str = None):
        if idempotency_key:
            if ProcessedMessage.objects.filter(message_id=idempotency_key).exists():
                return
            ProcessedMessage.objects.create(message_id=idempotency_key)

        try:
            batch = ReservationBatch.objects.get(order_id=order_id)
        except ReservationBatch.DoesNotExist:
            return

        if batch.status == 'CONFIRMED':
            return  # Idempotent skip

        batch.status = 'CONFIRMED'
        batch.save()

        items = StockReservation.objects.filter(batch=batch, status='PENDING')
        for item in items:
            item.status = 'CONFIRMED'
            item.save()

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE inventory_inventory 
                    SET reserved_stock = reserved_stock - %s,
                        total_stock = total_stock - %s,
                        version = version + 1,
                        updated_at = %s
                    WHERE variant_id = %s
                    RETURNING total_stock, available_stock, reserved_stock
                    """,
                    [item.quantity, item.quantity, timezone.now(), item.variant_id]
                )
                row = cursor.fetchone()
                total_stock, available_stock, reserved_stock = row

            InventoryMovement.objects.create(
                variant_id=item.variant_id,
                type='CONFIRM',
                quantity=item.quantity,
                available_before=available_stock,
                available_after=available_stock,
                reserved_before=reserved_stock + item.quantity,
                reserved_after=reserved_stock,
                total_before=total_stock + item.quantity,
                total_after=total_stock,
                reference_id=batch.batch_id
            )

        OutboxEvent.objects.create(
            aggregate_id=batch.batch_id,
            aggregate_type='ReservationBatch',
            event_type='inventory.stock.confirmed',
            message_id=uuid.uuid4(),
            payload={
                "event_version": "v1",
                "order_id": str(order_id),
                "correlation_id": str(batch.correlation_id)
            }
        )

    @staticmethod
    @transaction.atomic
    def release_reservation(order_id: str, reason: str = 'RELEASED', idempotency_key: str = None):
        if idempotency_key:
            if ProcessedMessage.objects.filter(message_id=idempotency_key).exists():
                return
            ProcessedMessage.objects.create(message_id=idempotency_key)

        try:
            batch = ReservationBatch.objects.get(order_id=order_id)
        except ReservationBatch.DoesNotExist:
            return

        if batch.status in ['RELEASED', 'EXPIRED']:
            return

        batch.status = reason
        batch.save()

        items = StockReservation.objects.filter(batch=batch, status='PENDING')
        for item in items:
            item.status = reason
            item.save()

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE inventory_inventory 
                    SET available_stock = available_stock + %s,
                        reserved_stock = reserved_stock - %s,
                        version = version + 1,
                        updated_at = %s
                    WHERE variant_id = %s
                    RETURNING total_stock, available_stock, reserved_stock
                    """,
                    [item.quantity, item.quantity, timezone.now(), item.variant_id]
                )
                row = cursor.fetchone()
                total_stock, available_stock, reserved_stock = row

            InventoryMovement.objects.create(
                variant_id=item.variant_id,
                type='RELEASE',
                quantity=item.quantity,
                available_before=available_stock - item.quantity,
                available_after=available_stock,
                reserved_before=reserved_stock + item.quantity,
                reserved_after=reserved_stock,
                total_before=total_stock,
                total_after=total_stock,
                reference_id=batch.batch_id
            )

        event_type = 'inventory.stock.expired' if reason == 'EXPIRED' else 'inventory.stock.released'
        OutboxEvent.objects.create(
            aggregate_id=batch.batch_id,
            aggregate_type='ReservationBatch',
            event_type=event_type,
            message_id=uuid.uuid4(),
            payload={
                "event_version": "v1",
                "order_id": str(order_id),
                "correlation_id": str(batch.correlation_id),
                "reason": reason
            }
        )

    @staticmethod
    @transaction.atomic
    def adjust_stock(variant_id: str, quantity: int, user_id: str = None):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE inventory_inventory 
                SET total_stock = total_stock + %s,
                    available_stock = available_stock + %s,
                    version = version + 1,
                    updated_at = %s
                WHERE variant_id = %s
                RETURNING total_stock, available_stock, reserved_stock
                """,
                [quantity, quantity, timezone.now(), variant_id]
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError("Variant not found")
            total_stock, available_stock, reserved_stock = row

        InventoryMovement.objects.create(
            variant_id=variant_id,
            type='ADJUSTMENT',
            quantity=quantity,
            available_before=available_stock - quantity,
            available_after=available_stock,
            reserved_before=reserved_stock,
            reserved_after=reserved_stock,
            total_before=total_stock - quantity,
            total_after=total_stock,
            reference_id=None
        )

        OutboxEvent.objects.create(
            aggregate_id=variant_id,
            aggregate_type='Inventory',
            event_type='inventory.stock.adjusted',
            message_id=uuid.uuid4(),
            payload={
                "event_version": "v1",
                "variant_id": str(variant_id),
                "quantity_changed": quantity,
                "user_id": str(user_id) if user_id else None
            }
        )
        InventoryService._check_low_stock(variant_id, available_stock)

    @staticmethod
    @transaction.atomic
    def purchase_stock(variant_id: str, quantity: int, user_id: str = None):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE inventory_inventory 
                SET total_stock = total_stock + %s,
                    available_stock = available_stock + %s,
                    version = version + 1,
                    updated_at = %s
                WHERE variant_id = %s
                RETURNING total_stock, available_stock, reserved_stock
                """,
                [quantity, quantity, timezone.now(), variant_id]
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError("Variant not found")
            total_stock, available_stock, reserved_stock = row

        InventoryMovement.objects.create(
            variant_id=variant_id,
            type='PURCHASE',
            quantity=quantity,
            available_before=available_stock - quantity,
            available_after=available_stock,
            reserved_before=reserved_stock,
            reserved_after=reserved_stock,
            total_before=total_stock - quantity,
            total_after=total_stock,
            reference_id=None
        )

        OutboxEvent.objects.create(
            aggregate_id=variant_id,
            aggregate_type='Inventory',
            event_type='inventory.stock.purchased',
            message_id=uuid.uuid4(),
            payload={
                "event_version": "v1",
                "variant_id": str(variant_id),
                "quantity": quantity,
                "user_id": str(user_id) if user_id else None
            }
        )
        InventoryService._check_low_stock(variant_id, available_stock)

    @staticmethod
    def _check_low_stock(variant_id, available_stock):
        threshold = int(os.environ.get('LOW_STOCK_THRESHOLD', '10'))
        if available_stock == 0:
            OutboxEvent.objects.create(
                aggregate_id=variant_id,
                aggregate_type='Inventory',
                event_type='inventory.stock.out_of_stock',
                message_id=uuid.uuid4(),
                payload={"event_version": "v1", "variant_id": str(variant_id)}
            )
        elif available_stock <= threshold:
            OutboxEvent.objects.create(
                aggregate_id=variant_id,
                aggregate_type='Inventory',
                event_type='inventory.stock.low',
                message_id=uuid.uuid4(),
                payload={"event_version": "v1", "variant_id": str(variant_id), "stock": available_stock}
            )
