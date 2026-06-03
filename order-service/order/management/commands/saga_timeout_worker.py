from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from order.models import OrderSaga
from order.services.saga_manager import OrderSagaManager

class Command(BaseCommand):
    help = 'Reap hung order sagas and trigger rollbacks'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting saga timeout worker...")
        
        while True:
            with transaction.atomic():
                hung_sagas = OrderSaga.objects.select_for_update(skip_locked=True).filter(
                    status='PENDING',
                    timeout_at__lt=timezone.now()
                )

                for saga in hung_sagas:
                    try:
                        self.stdout.write(self.style.WARNING(f"Timing out hung saga for order {saga.order_id}"))
                        
                        saga.status = 'FAILED'
                        saga.last_error = 'Saga Timeout Reached'
                        saga.save()
                        
                        OrderSagaManager.trigger_rollback(str(saga.order_id), 'SAGA_TIMEOUT')
                        
                        self.stdout.write(self.style.SUCCESS(f"Successfully rolled back order {saga.order_id}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error timing out order {saga.order_id}: {e}"))
            
            import time
            time.sleep(15)
