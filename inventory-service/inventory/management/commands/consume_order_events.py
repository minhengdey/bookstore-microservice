import json
import os
import pika
import logging
import time
from django.core.management.base import BaseCommand
from inventory.services.inventory_service import InventoryService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Consume order_events to trigger stock reservation"

    def handle(self, *args, **kwargs):
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

        # DLX
        channel.exchange_declare(exchange="dlx", exchange_type="direct", durable=True)
        channel.queue_declare(queue="inventory.dlq", durable=True)
        channel.queue_bind(exchange="dlx", queue="inventory.dlq", routing_key="inventory.events")

        # Order events exchange (fanout — published by order-outbox-worker)
        channel.exchange_declare(exchange="order_events", exchange_type="fanout", durable=True)
        queue_args = {
            "x-dead-letter-exchange": "dlx",
            "x-dead-letter-routing-key": "inventory.events",
        }
        result = channel.queue_declare(
            queue="inventory_order_consumer", durable=True, arguments=queue_args
        )
        queue_name = result.method.queue
        channel.queue_bind(exchange="order_events", queue=queue_name, routing_key="")

        self.stdout.write(self.style.SUCCESS("Inventory order consumer waiting for order_events..."))

        def callback(ch, method, properties, body):
            try:
                payload = json.loads(body)
                event_type = payload.get("event_type")

                # Support both wrapped (enterprise schema) and flat payloads
                if "data" in payload and isinstance(payload["data"], dict):
                    data = payload["data"]
                else:
                    data = payload

                logger.info(f"Received order event: {event_type}")

                if event_type in ("order.checkout.started", "order_created"):
                    order_id = data.get("order_id")
                    items = data.get("items", [])
                    correlation_id = data.get("correlation_id")

                    if not order_id:
                        raise ValueError("Missing order_id in payload")
                    if not items:
                        raise ValueError(f"No items in order {order_id}")

                    # Use correlation_id as idempotency key
                    idempotency_key = str(correlation_id) if correlation_id else str(order_id)

                    InventoryService.reserve_stock(
                        order_id=order_id,
                        items=items,
                        correlation_id=correlation_id,
                        idempotency_key=idempotency_key,
                    )
                    logger.info(f"Stock reserved for order {order_id}")

                elif event_type == "inventory.stock.confirm.requested":
                    order_id = data.get("order_id")
                    correlation_id = data.get("correlation_id")
                    if not order_id:
                        raise ValueError("Missing order_id in confirm request")
                    InventoryService.confirm_reservation(
                        order_id=order_id,
                        idempotency_key=f"confirm-{order_id}",
                    )
                    logger.info(f"Stock confirmed for order {order_id}")

                elif event_type in ("inventory.stock.release.requested", "order.cancelled"):
                    order_id = data.get("order_id")
                    reason = data.get("reason", "RELEASED")
                    if not order_id:
                        raise ValueError("Missing order_id in release request")
                    InventoryService.release_reservation(
                        order_id=order_id,
                        reason=reason,
                        idempotency_key=f"release-{order_id}",
                    )
                    logger.info(f"Stock released for order {order_id}")

                else:
                    logger.debug(f"Ignoring unhandled event_type: {event_type}")

                ch.basic_ack(delivery_tag=method.delivery_tag)

            except Exception as e:
                logger.error(f"Error processing order event: {e}", exc_info=True)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=queue_name, on_message_callback=callback)
        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
            self.stdout.write(self.style.WARNING("Inventory order consumer stopped."))
