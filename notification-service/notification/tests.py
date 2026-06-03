from django.test import TestCase
from unittest.mock import patch
import uuid
from notification.models import NotificationTemplate, UserContactProjection, NotificationLog, ProcessedEvent
from notification.services.notification_manager import NotificationManager

class NotificationManagerTests(TestCase):
    def setUp(self):
        self.user_id = str(uuid.uuid4())
        self.event_id = str(uuid.uuid4())
        
        # Setup projection
        UserContactProjection.objects.create(
            user_id=self.user_id,
            email='test@example.com',
            phone='1234567890',
            preferences={"payment.succeeded": {"email": True, "sms": False}}
        )
        
        # Setup templates
        NotificationTemplate.objects.create(
            event_type='payment.succeeded',
            channel='EMAIL',
            locale='vi',
            subject_template='Order {{ order_id }} Receipt',
            body_template='Amount: {{ final_amount }}',
            is_active=True
        )
        
        NotificationTemplate.objects.create(
            event_type='payment.succeeded',
            channel='SMS',
            locale='vi',
            subject_template=None,
            body_template='Order {{ order_id }} paid',
            is_active=True
        )

    def test_process_event_with_preferences(self):
        payload = {
            'user_id': self.user_id,
            'order_id': 'ORD-123',
            'final_amount': 500.0,
            'locale': 'vi'
        }
        
        NotificationManager.process_event(self.event_id, 'payment.succeeded', payload)
        
        # Should only send EMAIL, because SMS is turned off in preferences
        self.assertEqual(NotificationLog.objects.count(), 1)
        
        log = NotificationLog.objects.first()
        self.assertEqual(log.channel, 'EMAIL')
        self.assertEqual(log.recipient, 'test@example.com')
        self.assertEqual(log.subject, 'Order ORD-123 Receipt')
        self.assertEqual(log.body, 'Amount: 500.0')
        self.assertEqual(log.status, 'SENT')
        self.assertEqual(log.provider_used, 'MockEmailProvider')
        
        # Inbox pattern verification
        self.assertTrue(ProcessedEvent.objects.filter(event_id=self.event_id).exists())

    def test_inbox_pattern_replay(self):
        payload = {
            'user_id': self.user_id,
            'order_id': 'ORD-123',
            'final_amount': 500.0
        }
        
        NotificationManager.process_event(self.event_id, 'payment.succeeded', payload)
        self.assertEqual(NotificationLog.objects.count(), 1)
        
        # Replay event
        NotificationManager.process_event(self.event_id, 'payment.succeeded', payload)
        
        # Should still be 1 log
        self.assertEqual(NotificationLog.objects.count(), 1)
