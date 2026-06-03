from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import logging
from notification.models import NotificationLog
from notification.services.notification_manager import NotificationManager

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Retry failed notifications with exponential backoff'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting notification_retry_worker...")
        
        # Exponential backoff array in minutes
        BACKOFF_MINUTES = [1, 5, 15, 60, 240]
        MAX_RETRIES = len(BACKOFF_MINUTES)
        
        while True:
            now = timezone.now()
            
            # Find logs that need to be retired
            logs_to_retry = NotificationLog.objects.filter(
                status='RETRYING'
            ).exclude(
                next_retry_at__gt=now
            )
            
            for log in logs_to_retry:
                self.stdout.write(f"Retrying log {log.id} (Attempt {log.retry_count + 1})")
                
                NotificationManager._dispatch(log)
                
                # Setup next retry if it failed again
                if log.status in ['FAILED', 'RETRYING']:
                    log.retry_count += 1
                    
                    if log.retry_count >= MAX_RETRIES:
                        self.stdout.write(self.style.ERROR(f"Max retries reached for log {log.id}. Marking FAILED permanently."))
                        log.status = 'FAILED'
                        log.next_retry_at = None
                    else:
                        backoff = BACKOFF_MINUTES[log.retry_count]
                        log.status = 'RETRYING'
                        log.next_retry_at = now + timedelta(minutes=backoff)
                        self.stdout.write(self.style.WARNING(f"Will retry log {log.id} in {backoff} minutes."))
                        
                    log.save(update_fields=['status', 'retry_count', 'next_retry_at'])
                
            import time
            time.sleep(15) # Check every 15s
