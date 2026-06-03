import time
import json
import logging
import os
import pika
from django.core.management.base import BaseCommand
from django.utils import timezone
from interaction.models import OutboxEvent

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Relay events from Outbox to RabbitMQ'

    def handle(self, *args, **options):
        self.stdout.write("Starting Interaction Outbox Relay Worker...")

        rabbitmq_url = os.environ.get('RABBITMQ_URL', 'amqp://guest:guest@rabbitmq:5672/')
        
        while True:
            try:
                parameters = pika.URLParameters(rabbitmq_url)
                connection = pika.BlockingConnection(parameters)
                channel = connection.channel()
                
                # DLX for Interaction Events
                channel.exchange_declare(exchange='interaction_events_dlx', exchange_type='direct', durable=True)
                channel.queue_declare(queue='interaction_events_dlq', durable=True)
                channel.queue_bind(exchange='interaction_events_dlx', queue='interaction_events_dlq', routing_key='dlq')

                # Interaction Events Exchange
                channel.exchange_declare(exchange='interaction_events', exchange_type='topic', durable=True)
                
                self.stdout.write(self.style.SUCCESS("Connected to RabbitMQ. Polling outbox..."))
                
                while True:
                    pending_events = OutboxEvent.objects.filter(status='PENDING').order_by('created_at')[:50]
                    
                    if not pending_events:
                        time.sleep(2)
                        continue
                        
                    for event in pending_events:
                        try:
                            channel.basic_publish(
                                exchange='interaction_events',
                                routing_key=event.event_type,
                                body=json.dumps(event.payload),
                                properties=pika.BasicProperties(
                                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,
                                    message_id=str(event.message_id),
                                    content_type='application/json',
                                )
                            )
                            
                            event.status = 'PUBLISHED'
                            event.processed_at = timezone.now()
                            event.save(update_fields=['status', 'processed_at'])
                            self.stdout.write(f"Published event {event.message_id}")
                            
                        except Exception as e:
                            logger.error(f"Failed to publish event {event.message_id}: {str(e)}")
                            event.retry_count += 1
                            event.last_error = str(e)
                            if event.retry_count > 3:
                                event.status = 'FAILED'
                                # Push to DLQ directly if we give up
                                try:
                                    channel.basic_publish(
                                        exchange='interaction_events_dlx',
                                        routing_key='dlq',
                                        body=json.dumps(event.payload),
                                        properties=pika.BasicProperties(
                                            delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,
                                            message_id=str(event.message_id),
                                            content_type='application/json',
                                        )
                                    )
                                except Exception as dlq_e:
                                    logger.error(f"Failed to publish to DLQ {event.message_id}: {str(dlq_e)}")
                            event.save(update_fields=['retry_count', 'last_error', 'status'])
                            
                    time.sleep(0.5)

            except pika.exceptions.AMQPConnectionError:
                self.stdout.write(self.style.ERROR("RabbitMQ connection lost. Retrying in 5 seconds..."))
                time.sleep(5)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Unexpected error: {str(e)}"))
                time.sleep(5)
