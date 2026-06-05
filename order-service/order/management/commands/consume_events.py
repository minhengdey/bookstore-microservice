import json
import os
import pika
from django.core.management.base import BaseCommand
from order.services.saga_manager import OrderSagaManager

class Command(BaseCommand):
    help = 'Consume events for Order Saga'

    def handle(self, *args, **kwargs):
        rabbitmq_url = os.environ.get('RABBITMQ_URL', 'amqp://guest:guest@rabbitmq:5672/')
        parameters = pika.URLParameters(rabbitmq_url)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        channel.exchange_declare(exchange='dlx', exchange_type='direct', durable=True)
        channel.queue_declare(queue='order.dlq', durable=True)
        channel.queue_bind(exchange='dlx', queue='order.dlq', routing_key='order.events')

        channel.exchange_declare(exchange='inventory_events', exchange_type='topic', durable=True)
        channel.exchange_declare(exchange='payment_events', exchange_type='topic', durable=True)
        
        queue_args = {
            'x-dead-letter-exchange': 'dlx',
            'x-dead-letter-routing-key': 'order.events'
        }
        result = channel.queue_declare(queue='order_saga_queue', durable=True, arguments=queue_args)
        queue_name = result.method.queue

        channel.queue_bind(exchange='inventory_events', queue=queue_name, routing_key='inventory.stock.reserved')
        channel.queue_bind(exchange='inventory_events', queue=queue_name, routing_key='inventory.stock.reservation_failed')
        channel.queue_bind(exchange='inventory_events', queue=queue_name, routing_key='inventory.stock.confirmed')
        channel.queue_bind(exchange='payment_events', queue=queue_name, routing_key='payment.succeeded')
        channel.queue_bind(exchange='payment_events', queue=queue_name, routing_key='payment_completed')
        channel.queue_bind(exchange='payment_events', queue=queue_name, routing_key='payment.failed')

        self.stdout.write("Waiting for saga events...")

        def callback(ch, method, properties, body):
            try:
                payload = json.loads(body)
                
                if 'data' in payload and 'event_type' in payload:
                    event_type = payload['event_type']
                    data = payload['data']
                    order_id = data.get('order_id')
                    routing_key = event_type
                else:
                    order_id = payload.get('order_id')
                    routing_key = method.routing_key

                self.stdout.write(f"Received {routing_key}")
                
                if not order_id:
                    raise ValueError("No order_id in payload")

                if routing_key == 'inventory.stock.reserved':
                    OrderSagaManager.handle_inventory_reserved(order_id)
                elif routing_key == 'inventory.stock.reservation_failed':
                    reason = payload.get('reason', 'Unknown out of stock') if 'data' not in payload else data.get('reason', 'Unknown out of stock')
                    OrderSagaManager.handle_inventory_reservation_failed(order_id, reason)
                elif routing_key == 'inventory.stock.confirmed':
                    OrderSagaManager.handle_inventory_confirmed(order_id)
                elif routing_key in ['payment.succeeded', 'payment_completed']:
                    OrderSagaManager.handle_payment_succeeded(order_id)
                elif routing_key in ['payment.failed', 'payment_failed']:
                    reason = payload.get('reason', 'Payment failed') if 'data' not in payload else data.get('reason', 'Payment failed')
                    OrderSagaManager.handle_payment_failed(order_id, reason)

                ch.basic_ack(delivery_tag=method.delivery_tag)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing message: {e}"))
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=queue_name, on_message_callback=callback)
        channel.start_consuming()
