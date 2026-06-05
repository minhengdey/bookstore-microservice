import json
import logging
import pika
import os
from django.core.management.base import BaseCommand
from payment.legacy_models import Payment, PaymentStatus, ShippingStatus, PaymentOutbox
from common.events import EventPublisher
from django.db import transaction

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Consume order_events to process payments"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Payment Consumer..."))
        
        channel = EventPublisher.get_channel()
        
        # Setup Queue
        queue_name = 'payment_order_consumer'
        channel.queue_declare(queue=queue_name, durable=True, arguments={
            'x-dead-letter-exchange': 'dlx',
            'x-dead-letter-routing-key': 'dlq'
        })
        channel.queue_bind(queue=queue_name, exchange='order_events', routing_key='')
        
        def callback(ch, method, properties, body):
            try:
                payload = json.loads(body)
                event_type = payload.get("event_type")
                
                # Support both wrapped (enterprise schema) and flat payloads
                if "data" in payload:
                    data = payload.get("data", {})
                else:
                    data = payload

                # order-service publishes 'order.checkout.started' via OutboxEvent
                if event_type in ("order.checkout.started", "order_created"):
                    order_id = data.get("order_id")
                    amount = float(data.get("total_amount", 0))
                    
                    if not order_id:
                        raise ValueError("Missing order_id")
                        
                    # Idempotency Check!
                    if Payment.objects.filter(order_id=order_id).exists():
                        logger.warning(f"Payment for order {order_id} already exists. Skipping.")
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        return
                    
                    logger.info(f"Processing payment for order {order_id}, amount={amount}")
                        
                    # Mock Process Payment
                    with transaction.atomic():
                        payment = Payment.objects.create(
                            order_id=order_id,
                            payment_amount=amount,
                            payment_method=None,
                            payment_status=PaymentStatus.COMPLETED,
                            shipping_status=ShippingStatus.PENDING
                        )
                        
                        outbox_payload = {
                            "payment_id": payment.id,
                            "order_id": order_id,
                            "amount": str(amount),
                            "shipping_status": payment.shipping_status
                        }
                        PaymentOutbox.objects.create(
                            aggregate_id=str(payment.id),
                            event_type="payment.succeeded",  # canonical event name
                            payload=outbox_payload
                        )
                    
                    logger.info(f"Successfully processed payment for order {order_id}")
                else:
                    logger.debug(f"Ignoring unhandled event_type: {event_type}")
                    
                # Acknowledge
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"Error processing order event: {e}")
                # Reject and send to DLQ
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_consume(queue=queue_name, on_message_callback=callback)
        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
