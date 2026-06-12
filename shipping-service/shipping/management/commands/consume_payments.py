import json
import logging
import os

from django.core.management.base import BaseCommand

from common.client import InternalClient
from common.events import EventPublisher
from shipping.services import ShippingService

logger = logging.getLogger(__name__)

PAYMENT_EVENTS = {"payment.succeeded", "payment_completed"}
ORDER_SERVICE_URL = os.environ.get("ORDER_SERVICE_URL", "http://order-service:8000")
PAY_SERVICE_URL = os.environ.get("PAY_SERVICE_URL", "http://payment-service:8000")


class Command(BaseCommand):
    help = "Consume payment_events to create shipping records in DB"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Shipping Consumer..."))
        ship_svc = ShippingService()
        order_client = InternalClient()
        pay_client = InternalClient()

        channel = EventPublisher.get_channel()
        queue_name = "shipping_payment_consumer"
        channel.queue_declare(
            queue=queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "dlx",
                "x-dead-letter-routing-key": "dlq",
            },
        )
        channel.queue_bind(queue=queue_name, exchange="payment_events", routing_key="")

        def _notify_payment(order_id, shipping_status, failure_reason=""):
            try:
                pay_client.post(
                    f"{PAY_SERVICE_URL}/payments/internal/{order_id}/shipping-status/",
                    json={
                        "shipping_status": shipping_status,
                        "shipping_failure_reason": failure_reason,
                    },
                )
            except Exception as exc:
                logger.warning(f"Failed to update payment shipping status for order {order_id}: {exc}")

        def callback(ch, method, properties, body):
            order_id = None
            try:
                payload = json.loads(body)
                event_type = payload.get("event_type")
                if event_type not in PAYMENT_EVENTS:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return

                data = payload.get("data", {})
                order_id = data.get("order_id")
                if not order_id:
                    raise ValueError("Missing order_id")

                resp = order_client.get(
                    f"{ORDER_SERVICE_URL}/orders/internal/{order_id}/shipping-context/"
                )
                if resp.status_code != 200:
                    raise ValueError(f"Order shipping context unavailable: {resp.status_code}")

                context = resp.json()
                ship_svc.create_shipping(
                    int(order_id),
                    shipping_method_id=context.get("shipping_method_id"),
                    address_data=context.get("shipping_address_snapshot"),
                )
                _notify_payment(order_id, "processing")
                logger.info(f"Created shipping record for order {order_id}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"Error processing payment event: {e}")
                if order_id:
                    _notify_payment(order_id, "failed", str(e)[:500])
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_consume(queue=queue_name, on_message_callback=callback)
        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
