import uuid
import hashlib
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import logging

from payment.models import PaymentIntent, PaymentTransaction, OutboxEvent, ProcessedMessage, ProcessedWebhook
from payment.providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

class PaymentService:
    @staticmethod
    @transaction.atomic
    def create_payment(order_id: str, amount: float, correlation_id: str, idempotency_key: str = None) -> dict:
        if idempotency_key:
            if ProcessedMessage.objects.filter(message_id=idempotency_key).exists():
                existing = PaymentIntent.objects.filter(order_id=order_id).first()
                if existing:
                    return {
                        'payment_id': str(existing.id),
                        'provider': existing.provider,
                        'client_secret': existing.client_secret
                    }
            ProcessedMessage.objects.create(message_id=idempotency_key)

        provider = ProviderFactory.get_provider()
        intent_data = provider.create_intent(order_id, amount, 'USD')
        
        intent = PaymentIntent.objects.create(
            order_id=order_id,
            correlation_id=correlation_id,
            amount=Decimal(str(amount)),
            provider=os.environ.get('PAYMENT_PROVIDER', 'MOCK').upper(),
            provider_intent_id=intent_data.get('provider_intent_id'),
            client_secret=intent_data.get('client_secret'),
            expires_at=timezone.now() + timedelta(minutes=15),
            status='PENDING'
        )
        
        return {
            'payment_id': str(intent.id),
            'provider': intent.provider,
            'client_secret': intent.client_secret
        }

    @staticmethod
    @transaction.atomic
    def process_webhook(provider_name: str, payload: dict, signature: str) -> None:
        provider = ProviderFactory.get_provider(provider_name)
        
        provider_event_id = payload.get('id')
        if not provider_event_id:
            raise ValueError("Webhook missing event id")
            
        # Replay protection
        sig_hash = hashlib.sha256(signature.encode('utf-8')).hexdigest()
        if ProcessedWebhook.objects.filter(provider_event_id=provider_event_id).exists():
            logger.info(f"Webhook {provider_event_id} already processed. Ignoring.")
            return

        ProcessedWebhook.objects.create(
            provider_event_id=provider_event_id,
            signature_hash=sig_hash
        )
        
        # Normalize event
        event_data = provider.process_webhook(payload, signature)
        
        # Find intent
        # In a real system, provider might send client_reference_id or similar.
        # For mock, we'll try to find any pending intent for demonstration, or we need provider_intent_id in payload.
        # Assuming payload has something linking it back.
        provider_intent_id = payload.get('payment_intent_id') # Varies by provider
        intent = PaymentIntent.objects.filter(provider_intent_id=provider_intent_id).first()
        
        if not intent:
            # Maybe log it, could be a refund or orphaned payment
            logger.warning(f"No intent found for provider_intent_id {provider_intent_id}")
            return
            
        PaymentTransaction.objects.create(
            intent=intent,
            transaction_type=event_data['transaction_type'],
            provider_transaction_id=provider_event_id,
            amount=event_data['amount'],
            status=event_data['status'],
            gateway_status=event_data['gateway_status'],
            provider_fee=event_data['provider_fee'],
            raw_response=payload
        )
        
        if event_data['transaction_type'] == 'CHARGE':
            if event_data['status'] == 'SUCCEEDED':
                intent.status = 'SUCCEEDED'
                event_type = 'payment.succeeded'
            else:
                intent.status = 'FAILED'
                event_type = 'payment.failed'
        else:
            if event_data['status'] == 'SUCCEEDED':
                intent.status = 'REFUNDED'
                event_type = 'payment.refunded'
            else:
                intent.status = 'REFUND_PENDING'
                event_type = 'payment.refund_failed'
                
        intent.save()
        
        OutboxEvent.objects.create(
            aggregate_id=intent.id,
            aggregate_type='PaymentIntent',
            event_type=event_type,
            message_id=uuid.uuid4(),
            payload={
                "event_id": str(uuid.uuid4()),
                "event_type": event_type,
                "event_version": "v1",
                "correlation_id": str(intent.correlation_id),
                "causation_id": provider_event_id,
                "occurred_at": timezone.now().isoformat(),
                "order_id": str(intent.order_id)
            }
        )

    @staticmethod
    @transaction.atomic
    def refund_payment(payment_id: str, reason: str, idempotency_key: str = None) -> dict:
        if idempotency_key:
            if ProcessedMessage.objects.filter(message_id=idempotency_key).exists():
                intent = PaymentIntent.objects.filter(id=payment_id).first()
                return {"status": intent.status if intent else "UNKNOWN"}
            ProcessedMessage.objects.create(message_id=idempotency_key)

        intent = PaymentIntent.objects.get(id=payment_id)
        if intent.status not in ['SUCCEEDED', 'PROCESSING']:
            raise ValueError(f"Cannot refund payment in status {intent.status}")
            
        intent.status = 'REFUND_PENDING'
        intent.save()
        
        provider = ProviderFactory.get_provider(intent.provider)
        refund_data = provider.refund_payment(intent.provider_intent_id, float(intent.amount))
        
        PaymentTransaction.objects.create(
            intent=intent,
            transaction_type='REFUND',
            provider_transaction_id=refund_data['provider_event_id'],
            amount=refund_data['amount'],
            status=refund_data['status'],
            gateway_status=refund_data['gateway_status'],
            provider_fee=refund_data['provider_fee'],
            raw_response={"reason": reason}
        )
        
        if refund_data['status'] == 'SUCCEEDED':
            intent.status = 'REFUNDED'
            intent.save()
            
            OutboxEvent.objects.create(
                aggregate_id=intent.id,
                aggregate_type='PaymentIntent',
                event_type='payment.refunded',
                message_id=uuid.uuid4(),
                payload={
                    "event_id": str(uuid.uuid4()),
                    "event_type": "payment.refunded",
                    "event_version": "v1",
                    "correlation_id": str(intent.correlation_id),
                    "causation_id": refund_data['provider_event_id'],
                    "occurred_at": timezone.now().isoformat(),
                    "order_id": str(intent.order_id)
                }
            )
            
        return {"status": intent.status}
        
import os
