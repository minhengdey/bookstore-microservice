import json
import os
import pika
from django.core.management.base import BaseCommand
from notification.services.notification_manager import NotificationManager

class Command(BaseCommand):
    help = 'Consume events for Notifications'

    def handle(self, *args, **kwargs):
        rabbitmq_url = os.environ.get('RABBITMQ_URL', 'amqp://user:password@rabbitmq:5672/')
        parameters = pika.URLParameters(rabbitmq_url)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # DLX
        channel.exchange_declare(exchange='dlx', exchange_type='direct', durable=True)
        channel.queue_declare(queue='notification.dlq', durable=True)
        channel.queue_bind(exchange='dlx', queue='notification.dlq', routing_key='notification.events')

        # Domain Exchanges
        channel.exchange_declare(exchange='order_events', exchange_type='fanout', durable=True)
        channel.exchange_declare(exchange='payment_events', exchange_type='fanout', durable=True)
        channel.exchange_declare(exchange='user_events', exchange_type='topic', durable=True)
        
        queue_args = {
            'x-dead-letter-exchange': 'dlx',
            'x-dead-letter-routing-key': 'notification.events'
        }
        
        # User Sync Queue (Build Projection)
        user_q = channel.queue_declare(queue='notification_user_sync', durable=True, arguments=queue_args)
        channel.queue_bind(exchange='user_events', queue=user_q.method.queue, routing_key='user.#')
        
        # Notification Trigger Queue
        notif_q = channel.queue_declare(queue='notification_trigger_queue', durable=True, arguments=queue_args)
        channel.queue_bind(exchange='order_events', queue=notif_q.method.queue, routing_key='order.checkout.started')
        channel.queue_bind(exchange='order_events', queue=notif_q.method.queue, routing_key='order.cancelled')
        channel.queue_bind(exchange='payment_events', queue=notif_q.method.queue, routing_key='payment.succeeded')
        channel.queue_bind(exchange='payment_events', queue=notif_q.method.queue, routing_key='payment.failed')
        channel.queue_bind(exchange='payment_events', queue=notif_q.method.queue, routing_key='payment.refunded')

        self.stdout.write("Waiting for notification events...")

        def user_callback(ch, method, properties, body):
            try:
                payload = json.loads(body)
                routing_key = method.routing_key
                self.stdout.write(f"Received User Sync Event: {routing_key}")
                NotificationManager.process_user_event(routing_key, payload)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing user sync: {e}"))
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        def notif_callback(ch, method, properties, body):
            try:
                payload = json.loads(body)
                routing_key = method.routing_key
                self.stdout.write(f"Received Notification Trigger: {routing_key}")
                
                event_id = payload.get('event_id')
                if not event_id:
                    self.stdout.write(self.style.WARNING("Missing event_id, skipping duplicate protection"))
                    event_id = f"temp_{method.delivery_tag}"
                    
                correlation_id = payload.get('correlation_id')
                
                NotificationManager.process_event(event_id, routing_key, payload, correlation_id)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing notification trigger: {e}"))
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_qos(prefetch_count=5)
        channel.basic_consume(queue=user_q.method.queue, on_message_callback=user_callback)
        channel.basic_consume(queue=notif_q.method.queue, on_message_callback=notif_callback)
        
        channel.start_consuming()
