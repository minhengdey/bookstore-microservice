import time
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import now, timedelta
from product.models import StockReservationLog
from common.client import InternalClient
import os

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Reconcile orphaned stock reservations"

    def handle(self, *args, **options):
        client = InternalClient()
        order_url = os.environ.get("ORDER_SERVICE_URL", "http://order-service:8000")
        
        self.stdout.write(self.style.SUCCESS("Starting stock reconciliation worker..."))
        
        # Look for reservations older than 5 minutes that are still RESERVED
        cutoff_time = now() - timedelta(minutes=5)
        orphans = StockReservationLog.objects.filter(
            status="RESERVED",
            created_at__lt=cutoff_time
        ).order_by("created_at")
        
        if not orphans.exists():
            return
            
        # Group by order_id
        order_map = {}
        for log in orphans:
            order_map.setdefault(log.order_id, []).append(log)
            
        order_ids = list(order_map.keys())
        
        try:
            r = client.post(f"{order_url}/internal/orders/bulk-status/", json={"order_ids": order_ids})
            if r.status_code == 200:
                statuses = r.json().get("statuses", {})
                for order_id, logs in order_map.items():
                    # Statuses keys might be strings in JSON
                    status = statuses.get(str(order_id)) or statuses.get(order_id)
                    
                    if status in ["cancelled", "failed_payment", "refunded"]:
                        logger.warning(f"Reconciling orphaned stock for failed/cancelled order {order_id}")
                        self._force_release(order_id, logs)
                    elif status in ["paid", "shipped", "delivered", "pending_payment", "confirmed"]:
                        StockReservationLog.objects.filter(id__in=[l.id for l in logs]).update(status="COMMITTED")
                    elif status is None:
                        # Order doesn't exist (transaction rollback in order-service!)
                        logger.warning(f"Reconciling orphaned stock for non-existent order {order_id}")
                        self._force_release(order_id, logs)
        except Exception as e:
            logger.error(f"Bulk reconciliation error: {e}")

    def _force_release(self, order_id, logs):
        with transaction.atomic():
            for log in logs:
                # Lock row
                l = StockReservationLog.objects.select_for_update().get(id=log.id)
                if l.status == "RESERVED":
                    l.status = "RELEASED"
                    l.save(update_fields=["status"])
                    
                    product = l.product
                    product.stock += l.quantity
                    product.save(update_fields=["stock"])
                    
                    from product.services import invalidate_product_cache
                    invalidate_product_cache(product.id)
                    logger.info("metric_stock_reconciled", extra={"order_id": order_id, "product_id": product.id, "quantity": l.quantity})
