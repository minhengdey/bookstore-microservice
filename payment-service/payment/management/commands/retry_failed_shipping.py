import time
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import now
from payment.models import Payment, ShippingStatus
from common.client import InternalClient
import os

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Retry failed shipping requests"

    def handle(self, *args, **options):
        client = InternalClient()
        ship_url = os.environ.get("SHIP_SERVICE_URL", "http://shipping-service:8000")
        
        self.stdout.write(self.style.SUCCESS("Starting shipping retry worker..."))
        
        # We will loop infinitely in the bash script, but we can also just run it once per execution
        payments = Payment.objects.filter(
            shipping_status=ShippingStatus.FAILED,
            shipping_retry_count__lt=5
        ).order_by('shipping_retry_count', 'payment_date')
        
        for payment in payments:
            # Backoff logic based on retry_count: e.g. if count=1, wait 1m, count=2 wait 5m.
            # But since we run this as a cron, we'll just attempt it.
            logger.info("metric_shipping_retry_attempt", extra={
                "order_id": payment.order_id,
                "retry_count": payment.shipping_retry_count + 1
            })
            
            with transaction.atomic():
                # Lock row
                p = Payment.objects.select_for_update().get(id=payment.id)
                p.shipping_retry_count += 1
                p.save(update_fields=["shipping_retry_count"])
                
            try:
                r = client.post(f"{ship_url}/internal/shipping/create/", json={"order_id": payment.order_id})
                if r.status_code in (200, 201):
                    payment.shipping_status = ShippingStatus.PROCESSING
                    payment.shipping_failure_reason = ""
                    payment.save(update_fields=["shipping_status", "shipping_failure_reason"])
                    logger.info("metric_shipping_retry_success", extra={"order_id": payment.order_id})
                    self.stdout.write(self.style.SUCCESS(f"Successfully recovered shipping for order {payment.order_id}"))
                else:
                    raise Exception(f"Status {r.status_code}: {r.text}")
            except Exception as e:
                err_msg = f"Retry {payment.shipping_retry_count} failed: {type(e).__name__}: {str(e)}"
                payment.shipping_failure_reason = err_msg[:500]
                payment.save(update_fields=["shipping_failure_reason"])
                logger.warning(f"Failed to retry shipping for order {payment.order_id}: {e}")
