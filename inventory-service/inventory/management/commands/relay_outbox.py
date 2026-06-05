import time
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import now
import os
import pika
import json

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Relay InventoryOutbox events to RabbitMQ (inventory_events exchange)"

    def handle(self, *args, **options):
        from inventory.models import OutboxEvent

        self.stdout.write(self.style.SUCCESS("Starting Inventory Outbox Relay worker..."))

        rabbitmq_url = os.environ.get("RABBITMQ_URL", "amqp://user:password@rabbitmq:5672/")
        max_retries = int(os.environ.get("RABBITMQ_CONN_RETRIES", "10"))
        delay = float(os.environ.get("RABBITMQ_CONN_DELAY", "3"))

        connection = None
        for attempt in range(1, max_retries + 1):
            try:
                parameters = pika.URLParameters(rabbitmq_url)
                connection = pika.BlockingConnection(parameters)
                break
            except Exception as e:
                logger.warning(f"RabbitMQ connection attempt {attempt} failed: {e}")
                if attempt == max_retries:
                    raise
                time.sleep(delay)

        channel = connection.channel()
        channel.exchange_declare(exchange="inventory_events", exchange_type="topic", durable=True)
        self.stdout.write(self.style.SUCCESS("Connected to RabbitMQ. Polling inventory outbox..."))

        while True:
            try:
                events = OutboxEvent.objects.filter(status="PENDING").order_by("created_at")[:50]

                if not events:
                    time.sleep(2)
                    continue

                for event in events:
                    with transaction.atomic():
                        e = OutboxEvent.objects.select_for_update().get(id=event.id)

                        if e.status != "PENDING":
                            continue

                        try:
                            # Wrap in enterprise event schema
                            full_payload = {
                                "event_type": e.event_type,
                                "version": 1,
                                "data": e.payload,
                            }
                            channel.basic_publish(
                                exchange="inventory_events",
                                routing_key=e.event_type,  # topic routing key e.g. inventory.stock.reserved
                                body=json.dumps(full_payload),
                                properties=pika.BasicProperties(
                                    delivery_mode=2,  # persistent
                                ),
                            )
                            e.status = "PUBLISHED"
                            e.processed_at = now()
                            e.save(update_fields=["status", "processed_at"])
                            logger.info(f"Published inventory event {e.event_type} for aggregate {e.aggregate_id}")
                        except Exception as err:
                            e.retry_count += 1
                            e.last_error = str(err)[:500]
                            if e.retry_count >= 5:
                                e.status = "FAILED"
                            e.save(update_fields=["retry_count", "last_error", "status"])
                            logger.error(f"Failed to publish inventory outbox event {e.id}: {err}")
                            # Try to reconnect
                            try:
                                if connection.is_closed:
                                    connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
                                    channel = connection.channel()
                                    channel.exchange_declare(exchange="inventory_events", exchange_type="topic", durable=True)
                            except Exception:
                                pass

                time.sleep(0.5)

            except Exception as loop_err:
                logger.error(f"Relay loop error: {loop_err}")
                time.sleep(5)
