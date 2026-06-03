from django.test import TestCase
from unittest.mock import patch
import uuid
from decimal import Decimal

from payment.models import PaymentIntent, PaymentTransaction, OutboxEvent, ProcessedWebhook
from payment.services.payment_service import PaymentService
from payment.providers.mock_provider import MockProvider

class PaymentServiceTests(TestCase):
    def setUp(self):
        self.order_id = str(uuid.uuid4())
        self.correlation_id = str(uuid.uuid4())

    def test_create_payment_idempotency(self):
        idempotency_key = "test_key_123"
        
        # First call creates the intent
        res1 = PaymentService.create_payment(self.order_id, 100.0, self.correlation_id, idempotency_key)
        self.assertIn('payment_id', res1)
        
        # Second call with same key returns the exact same result without duplicate DB entry
        res2 = PaymentService.create_payment(self.order_id, 100.0, self.correlation_id, idempotency_key)
        self.assertEqual(res1['payment_id'], res2['payment_id'])
        
        # Verify only 1 intent exists
        self.assertEqual(PaymentIntent.objects.filter(order_id=self.order_id).count(), 1)

    def test_process_webhook_success(self):
        # 1. Create intent
        res = PaymentService.create_payment(self.order_id, 100.0, self.correlation_id)
        payment_id = res['payment_id']
        intent = PaymentIntent.objects.get(id=payment_id)
        
        # 2. Simulate webhook
        payload = {
            'id': 'evt_mock_success_123',
            'type': 'payment_intent.succeeded',
            'amount': 100.0,
            'payment_intent_id': intent.provider_intent_id
        }
        
        PaymentService.process_webhook('MOCK', payload, 'sig_hash_mock')
        
        intent.refresh_from_db()
        self.assertEqual(intent.status, 'SUCCEEDED')
        
        self.assertEqual(PaymentTransaction.objects.count(), 1)
        self.assertEqual(OutboxEvent.objects.filter(event_type='payment.succeeded').count(), 1)
        self.assertEqual(ProcessedWebhook.objects.count(), 1)

    def test_process_webhook_replay_protection(self):
        res = PaymentService.create_payment(self.order_id, 100.0, self.correlation_id)
        intent = PaymentIntent.objects.get(id=res['payment_id'])
        
        payload = {
            'id': 'evt_mock_replay_123',
            'type': 'payment_intent.succeeded',
            'payment_intent_id': intent.provider_intent_id
        }
        
        # Call 3 times
        PaymentService.process_webhook('MOCK', payload, 'sig_hash_1')
        PaymentService.process_webhook('MOCK', payload, 'sig_hash_1')
        PaymentService.process_webhook('MOCK', payload, 'sig_hash_1')
        
        # Should only be processed once
        self.assertEqual(PaymentTransaction.objects.count(), 1)
        self.assertEqual(OutboxEvent.objects.count(), 1)

    def test_refund_payment(self):
        res = PaymentService.create_payment(self.order_id, 100.0, self.correlation_id)
        intent = PaymentIntent.objects.get(id=res['payment_id'])
        
        # Force to SUCCEEDED so we can refund
        intent.status = 'SUCCEEDED'
        intent.save()
        
        res_refund = PaymentService.refund_payment(str(intent.id), "User requested")
        self.assertEqual(res_refund['status'], 'REFUNDED')
        
        intent.refresh_from_db()
        self.assertEqual(intent.status, 'REFUNDED')
        
        self.assertEqual(PaymentTransaction.objects.filter(transaction_type='REFUND').count(), 1)
        self.assertEqual(OutboxEvent.objects.filter(event_type='payment.refunded').count(), 1)
