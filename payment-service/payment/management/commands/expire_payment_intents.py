import uuid
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from payment.models import PaymentIntent, OutboxEvent

class Command(BaseCommand):
    help = 'Expire old pending payment intents'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting expire_payment_intents worker...")
        
        while True:
            with transaction.atomic():
                expired_intents = PaymentIntent.objects.select_for_update(skip_locked=True).filter(
                    status='PENDING',
                    expires_at__lt=timezone.now()
                )

                for intent in expired_intents:
                    try:
                        self.stdout.write(self.style.WARNING(f"Expiring payment intent {intent.id}"))
                        
                        intent.status = 'EXPIRED'
                        intent.save()
                        
                        OutboxEvent.objects.create(
                            aggregate_id=intent.id,
                            aggregate_type='PaymentIntent',
                            event_type='payment.expired',
                            message_id=uuid.uuid4(),
                            payload={
                                "event_id": str(uuid.uuid4()),
                                "event_type": "payment.expired",
                                "event_version": "v1",
                                "correlation_id": str(intent.correlation_id),
                                "causation_id": str(intent.id),
                                "occurred_at": timezone.now().isoformat(),
                                "order_id": str(intent.order_id)
                            }
                        )
                        
                        self.stdout.write(self.style.SUCCESS(f"Successfully expired payment intent {intent.id}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error expiring intent {intent.id}: {e}"))
            
            import time
            time.sleep(15)
