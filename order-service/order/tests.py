from django.test import TestCase
from unittest.mock import patch
import uuid
from decimal import Decimal

from order.models import Order, OrderItem, OrderSaga, OrderStatusHistory
from order.services.saga_manager import OrderSagaManager
from order.services.cart_service import CartService

class MockVariantData:
    @staticmethod
    def get_variant(variant_id):
        return {
            'product_id': str(uuid.uuid4()),
            'variant_id': variant_id,
            'price': '100.00',
            'product_name': 'Test Product',
            'sku': 'TEST-SKU-1',
            'attributes': {'color': 'red'}
        }

class MockPaymentData:
    @staticmethod
    def create_payment_session(order_id, amount):
        return {
            'payment_id': str(uuid.uuid4()),
            'provider': 'STRIPE'
        }

class OrderSagaTests(TestCase):
    def setUp(self):
        self.user_id = str(uuid.uuid4())
        self.variant_id = str(uuid.uuid4())
        
    @patch('order.services.catalog_client.CatalogClient.get_variant', side_effect=MockVariantData.get_variant)
    @patch('order.services.payment_client.PaymentClient.create_payment_session', side_effect=MockPaymentData.create_payment_session)
    def test_full_success_checkout_flow(self, mock_payment, mock_catalog):
        # 1. Start Checkout
        cart_items = [{'variant_id': self.variant_id, 'quantity': 2}]
        shipping = {'address': '123 Test St'}
        
        order = OrderSagaManager.start_checkout(self.user_id, cart_items, shipping)
        
        self.assertEqual(order.status, 'RESERVING_STOCK')
        self.assertEqual(order.total_amount, Decimal('200.00'))
        
        saga = order.saga
        self.assertEqual(saga.current_step, 'INVENTORY_RESERVE')
        self.assertEqual(saga.status, 'PENDING')
        
        # 2. Inventory Reserved
        OrderSagaManager.handle_inventory_reserved(order.id)
        
        order.refresh_from_db()
        self.assertEqual(order.status, 'PAYMENT_PROCESSING')
        self.assertIsNotNone(order.payment_id)
        self.assertEqual(order.payment_provider, 'STRIPE')
        
        saga.refresh_from_db()
        self.assertEqual(saga.current_step, 'PAYMENT_CREATE')
        
        # 3. Payment Succeeded
        OrderSagaManager.handle_payment_succeeded(order.id)
        
        order.refresh_from_db()
        self.assertEqual(order.status, 'WAITING_INVENTORY_CONFIRM')
        
        # 4. Inventory Confirmed
        OrderSagaManager.handle_inventory_confirmed(order.id)
        
        order.refresh_from_db()
        self.assertEqual(order.status, 'COMPLETED')
        
        saga.refresh_from_db()
        self.assertEqual(saga.status, 'SUCCESS')

    @patch('order.services.catalog_client.CatalogClient.get_variant', side_effect=MockVariantData.get_variant)
    def test_rollback_on_out_of_stock(self, mock_catalog):
        # 1. Start Checkout
        cart_items = [{'variant_id': self.variant_id, 'quantity': 2}]
        shipping = {'address': '123 Test St'}
        
        order = OrderSagaManager.start_checkout(self.user_id, cart_items, shipping)
        
        # 2. Inventory Reservation Failed
        OrderSagaManager.handle_inventory_reservation_failed(order.id, 'Out of stock')
        
        order.refresh_from_db()
        self.assertEqual(order.status, 'CANCELLED')
        
        saga = order.saga
        self.assertEqual(saga.status, 'FAILED')
        self.assertEqual(saga.last_error, 'Out of stock')
        
    @patch('order.services.catalog_client.CatalogClient.get_variant', side_effect=MockVariantData.get_variant)
    @patch('order.services.payment_client.PaymentClient.create_payment_session', side_effect=MockPaymentData.create_payment_session)
    def test_rollback_on_payment_failed(self, mock_payment, mock_catalog):
        # 1. Start Checkout
        cart_items = [{'variant_id': self.variant_id, 'quantity': 2}]
        shipping = {'address': '123 Test St'}
        
        order = OrderSagaManager.start_checkout(self.user_id, cart_items, shipping)
        
        # 2. Inventory Reserved (triggers payment creation)
        OrderSagaManager.handle_inventory_reserved(order.id)
        
        # 3. Payment Failed (e.g. from webhook/event)
        OrderSagaManager.handle_payment_failed(order.id, 'Card declined')
        
        order.refresh_from_db()
        # It triggers trigger_rollback which sets status to CANCELLING then CANCELLED 
        self.assertEqual(order.status, 'CANCELLED')
        
        saga = order.saga
        self.assertEqual(saga.status, 'FAILED')
        self.assertEqual(saga.last_error, 'Card declined')
