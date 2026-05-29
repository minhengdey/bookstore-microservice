import json
import logging
import pika
from django.core.management.base import BaseCommand
from shipping.models import Shipping, ShippingStatus
from common.events import EventPublisher

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Consume payment_events to process shipping"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Shipping Consumer..."))
        
        channel = EventPublisher.get_channel()
        
        # Setup Queue
        queue_name = 'shipping_payment_consumer'
        channel.queue_declare(queue=queue_name, durable=True, arguments={
            'x-dead-letter-exchange': 'dlx',
            'x-dead-letter-routing-key': 'dlq'
        })
        channel.queue_bind(queue=queue_name, exchange='payment_events', routing_key='')
        
        def callback(ch, method, properties, body):
            try:
                payload = json.loads(body)
                event_type = payload.get("event_type")
                
                if event_type == "payment_completed":
                    data = payload.get("data", {})
                    order_id = data.get("order_id")
                    
                    if not order_id:
                        raise ValueError("Missing order_id")
                        
                    # Idempotency Check
                    shipping, created = Shipping.objects.get_or_create(order_id=order_id)
                    if not created and shipping.status != ShippingStatus.PENDING:
                        logger.warning(f"Shipping for order {order_id} already exists. Skipping.")
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        return
                        
                    shipping.status = ShippingStatus.PROCESSING
                    shipping.save(update_fields=["status"])
                    logger.info(f"Successfully processed shipping for order {order_id}")
                    
                # Acknowledge
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"Error processing payment event: {e}")
                # Reject and send to DLQ
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_consume(queue=queue_name, on_message_callback=callback)
        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
