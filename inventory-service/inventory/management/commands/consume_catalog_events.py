import json
import os
import pika
from django.core.management.base import BaseCommand
from inventory.models import Inventory

class Command(BaseCommand):
    help = 'Consume catalog events from RabbitMQ'

    def handle(self, *args, **kwargs):
        rabbitmq_url = os.environ.get('RABBITMQ_URL', 'amqp://guest:guest@rabbitmq:5672/')
        parameters = pika.URLParameters(rabbitmq_url)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # Set up Dead Letter Exchange & Queue
        channel.exchange_declare(exchange='dlx', exchange_type='direct', durable=True)
        channel.queue_declare(queue='inventory.dlq', durable=True)
        channel.queue_bind(exchange='dlx', queue='inventory.dlq', routing_key='inventory.events')

        # Declare the main exchange and queue with DLQ settings
        channel.exchange_declare(exchange='catalog_events', exchange_type='topic', durable=True)
        queue_args = {
            'x-dead-letter-exchange': 'dlx',
            'x-dead-letter-routing-key': 'inventory.events'
        }
        result = channel.queue_declare(queue='inventory_catalog_queue', durable=True, arguments=queue_args)
        queue_name = result.method.queue

        channel.queue_bind(exchange='catalog_events', queue=queue_name, routing_key='catalog.variant.*')

        self.stdout.write("Waiting for catalog events. To exit press CTRL+C")

        def callback(ch, method, properties, body):
            try:
                payload = json.loads(body)
                routing_key = method.routing_key
                self.stdout.write(f"Received {routing_key}")

                if routing_key == 'catalog.variant.created':
                    variant_id = payload.get('variant_id')
                    if variant_id:
                        Inventory.objects.get_or_create(
                            variant_id=variant_id,
                            defaults={
                                'total_stock': 0,
                                'available_stock': 0,
                                'reserved_stock': 0,
                                'version': 0,
                                'is_active': True
                            }
                        )
                        self.stdout.write(self.style.SUCCESS(f"Initialized stock for {variant_id}"))

                elif routing_key == 'catalog.variant.deleted':
                    variant_id = payload.get('variant_id')
                    if variant_id:
                        Inventory.objects.filter(variant_id=variant_id).update(is_active=False)
                        self.stdout.write(self.style.SUCCESS(f"Archived stock for {variant_id}"))

                ch.basic_ack(delivery_tag=method.delivery_tag)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing message: {e}"))
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False) # Send to DLQ

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=queue_name, on_message_callback=callback)
        channel.start_consuming()
