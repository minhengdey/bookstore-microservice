import uuid
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from payment.models import PaymentIntent, PaymentTransaction, OutboxEvent
from payment.providers.provider_factory import ProviderFactory

class Command(BaseCommand):
    help = 'Reconcile hung processing payments with gateway'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting payment_reconciliation_worker...")
        
        while True:
            with transaction.atomic():
                # Find intents stuck in PROCESSING (e.g. webhook dropped)
                stuck_intents = PaymentIntent.objects.select_for_update(skip_locked=True).filter(
                    status='PROCESSING'
                )

                for intent in stuck_intents:
                    try:
                        provider = ProviderFactory.get_provider(intent.provider)
                        gateway_state = provider.sync_status(intent.provider_intent_id)
                        
                        if gateway_state['status'] == 'SUCCEEDED':
                            self.stdout.write(self.style.SUCCESS(f"Reconciled stuck intent {intent.id} to SUCCEEDED"))
                            
                            intent.status = 'SUCCEEDED'
                            intent.save()
                            
                            PaymentTransaction.objects.create(
                                intent=intent,
                                transaction_type='CHARGE',
                                provider_transaction_id=f"reconcile_{uuid.uuid4().hex[:10]}",
                                amount=intent.amount,
                                status='SUCCEEDED',
                                gateway_status=gateway_state['gateway_status'],
                                raw_response={"source": "reconciliation_worker"}
                            )
                            
                            OutboxEvent.objects.create(
                                aggregate_id=intent.id,
                                aggregate_type='PaymentIntent',
                                event_type='payment.succeeded',
                                message_id=uuid.uuid4(),
                                payload={
                                    "event_id": str(uuid.uuid4()),
                                    "event_type": "payment.succeeded",
                                    "event_version": "v1",
                                    "correlation_id": str(intent.correlation_id),
                                    "causation_id": f"reconcile_{intent.id}",
                                    "occurred_at": timezone.now().isoformat(),
                                    "order_id": str(intent.order_id)
                                }
                            )
                            
                        elif gateway_state['status'] == 'FAILED':
                            self.stdout.write(self.style.WARNING(f"Reconciled stuck intent {intent.id} to FAILED"))
                            intent.status = 'FAILED'
                            intent.save()
                            # Emit failed event
                            OutboxEvent.objects.create(
                                aggregate_id=intent.id,
                                aggregate_type='PaymentIntent',
                                event_type='payment.failed',
                                message_id=uuid.uuid4(),
                                payload={
                                    "event_id": str(uuid.uuid4()),
                                    "event_type": "payment.failed",
                                    "event_version": "v1",
                                    "correlation_id": str(intent.correlation_id),
                                    "causation_id": f"reconcile_{intent.id}",
                                    "occurred_at": timezone.now().isoformat(),
                                    "order_id": str(intent.order_id)
                                }
                            )
                            
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error reconciling intent {intent.id}: {e}"))
            
            # Run every 30 minutes in production, but loop faster here for demo
            import time
            time.sleep(1800)
