from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from inventory.models import ReservationBatch
from inventory.services.inventory_service import InventoryService

class Command(BaseCommand):
    help = 'Release expired stock reservations'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting expired reservation worker...")
        
        while True:
            with transaction.atomic():
                expired_batches = ReservationBatch.objects.select_for_update(skip_locked=True).filter(
                    status='PENDING',
                    expires_at__lt=timezone.now()
                )

                for batch in expired_batches:
                    try:
                        InventoryService.release_reservation(
                            order_id=batch.order_id,
                            reason='EXPIRED'
                        )
                        self.stdout.write(self.style.SUCCESS(f"Expired batch for order {batch.order_id}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error expiring batch {batch.order_id}: {e}"))
            
            import time
            time.sleep(10)
