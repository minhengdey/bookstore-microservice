from django.test import TestCase
from django.db import transaction
import uuid

from inventory.models import Inventory, StockReservation, ReservationBatch, InventoryMovement, ProcessedMessage
from inventory.services.inventory_service import InventoryService, OutOfStockError, ConcurrentUpdateError

class InventoryServiceTests(TestCase):
    def setUp(self):
        self.variant_id = str(uuid.uuid4())
        self.order_id = str(uuid.uuid4())
        self.correlation_id = str(uuid.uuid4())
        
        self.inventory = Inventory.objects.create(
            variant_id=self.variant_id,
            total_stock=100,
            available_stock=100,
            reserved_stock=0,
            version=0,
            is_active=True
        )

    def test_reserve_stock_success(self):
        items = [{'variant_id': self.variant_id, 'quantity': 10}]
        idempotency_key = str(uuid.uuid4())
        
        batch = InventoryService.reserve_stock(
            order_id=self.order_id,
            correlation_id=self.correlation_id,
            items=items,
            idempotency_key=idempotency_key
        )

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.available_stock, 90)
        self.assertEqual(self.inventory.reserved_stock, 10)
        self.assertEqual(self.inventory.version, 1)

        # Check Movement
        movement = InventoryMovement.objects.get(variant_id=self.variant_id)
        self.assertEqual(movement.type, 'RESERVE')
        self.assertEqual(movement.available_before, 100)
        self.assertEqual(movement.available_after, 90)

    def test_reserve_out_of_stock(self):
        items = [{'variant_id': self.variant_id, 'quantity': 150}]
        
        with self.assertRaises(OutOfStockError):
            InventoryService.reserve_stock(
                order_id=self.order_id,
                items=items,
                idempotency_key=str(uuid.uuid4())
            )
            
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.available_stock, 100) # Unchanged

    def test_reserve_idempotency(self):
        items = [{'variant_id': self.variant_id, 'quantity': 10}]
        idempotency_key = str(uuid.uuid4())
        
        InventoryService.reserve_stock(
            order_id=self.order_id,
            items=items,
            idempotency_key=idempotency_key
        )
        
        # Second call with same idempotency key should just return without mutating
        res2 = InventoryService.reserve_stock(
            order_id=self.order_id,
            items=items,
            idempotency_key=idempotency_key
        )
        
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.available_stock, 90) # Deducted exactly once
        self.assertEqual(InventoryMovement.objects.count(), 1)
        self.assertIsNone(res2)

    def test_confirm_reservation(self):
        items = [{'variant_id': self.variant_id, 'quantity': 10}]
        batch = InventoryService.reserve_stock(order_id=self.order_id, items=items)
        
        InventoryService.confirm_reservation(order_id=self.order_id)
        
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.total_stock, 90)
        self.assertEqual(self.inventory.available_stock, 90)
        self.assertEqual(self.inventory.reserved_stock, 0)

        batch.refresh_from_db()
        self.assertEqual(batch.status, 'CONFIRMED')
        
    def test_release_reservation(self):
        items = [{'variant_id': self.variant_id, 'quantity': 10}]
        batch = InventoryService.reserve_stock(order_id=self.order_id, items=items)
        
        InventoryService.release_reservation(order_id=self.order_id, reason='EXPIRED')
        
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.total_stock, 100)
        self.assertEqual(self.inventory.available_stock, 100)
        self.assertEqual(self.inventory.reserved_stock, 0)

        batch.refresh_from_db()
        self.assertEqual(batch.status, 'EXPIRED')
