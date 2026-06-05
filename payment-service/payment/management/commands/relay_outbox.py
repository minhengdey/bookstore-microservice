import time
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import now
from payment.legacy_models import PaymentOutbox
from common.events import EventPublisher

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Relay PaymentOutbox events to RabbitMQ"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Payment Outbox Relay worker..."))
        
        while True:
            # Poll pending events
            events = PaymentOutbox.objects.filter(status="PENDING").order_by("created_at")[:50]
            
            if not events:
                time.sleep(2)
                continue
                
            for event in events:
                with transaction.atomic():
                    # Lock row
                    e = PaymentOutbox.objects.select_for_update().get(id=event.id)
                    
                    if e.status != "PENDING":
                        continue
                        
                    try:
                        EventPublisher.publish(
                            exchange="payment_events",
                            event_type=e.event_type,
                            data=e.payload,
                            version=1
                        )
                        e.status = "PUBLISHED"
                        e.published_at = now()
                        e.save(update_fields=["status", "published_at"])
                    except Exception as err:
                        e.retry_count += 1
                        e.error_message = str(err)[:500]
                        if e.retry_count >= 5:
                            e.status = "FAILED"
                        e.save(update_fields=["retry_count", "error_message", "status"])
                        logger.error(f"Failed to publish PaymentOutbox event {e.id}: {err}")
            
            time.sleep(0.5)
