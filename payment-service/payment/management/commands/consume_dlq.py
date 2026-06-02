import json
import logging
from django.core.management.base import BaseCommand
from payment.models import DLQEvent
from common.events import EventPublisher

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Consume messages from the Dead Letter Queue (dlq)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting DLQ Consumer..."))
        channel = EventPublisher.get_channel()

        # Idempotent re-declare
        channel.queue_declare(queue='dlq', durable=True)

        def on_dlq_message(ch, method, properties, body):
            raw = body.decode('utf-8', errors='replace')
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"_raw": raw}

            event_type = payload.get("event_type", "unknown")
            # data có thể là nested dict
            data = payload.get("data", {})
            if isinstance(data, dict):
                order_id = data.get("order_id", "unknown")
            else:
                order_id = "unknown"
            exchange    = getattr(method, 'exchange', '') or ""
            routing_key = getattr(method, 'routing_key', '') or ""

            logger.error(
                "DLQ message received: event_type=%s, order_id=%s, exchange=%s",
                event_type, order_id, exchange,
                extra={
                    "event_type": event_type,
                    "order_id": order_id,
                    "exchange": exchange,
                    "routing_key": routing_key,
                    "body": payload,
                }
            )

            try:
                DLQEvent.objects.create(
                    queue_name="dlq",
                    exchange=exchange,
                    routing_key=routing_key,
                    body=payload,
                    error_message=f"event_type={event_type}, order_id={order_id}",
                )
            except Exception as db_err:
                logger.error("Failed to save DLQEvent to DB: %s", db_err)
                # Still ack to avoid infinite requeue

            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_consume(queue='dlq', on_message_callback=on_dlq_message)
        self.stdout.write(self.style.SUCCESS("DLQ Consumer listening on 'dlq'..."))
        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
            self.stdout.write(self.style.WARNING("DLQ Consumer stopped."))
