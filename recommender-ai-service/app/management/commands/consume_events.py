import json
import os
import pika
import logging
from django.core.management.base import BaseCommand
from app.services.event_handler import EventHandler

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Consume events for Recommendation AI'

    def handle(self, *args, **kwargs):
        rabbitmq_url = os.environ.get('RABBITMQ_URL', 'amqp://guest:guest@rabbitmq:5672/')
        parameters = pika.URLParameters(rabbitmq_url)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # Exchanges
        channel.exchange_declare(exchange='user_events', exchange_type='topic', durable=True)
        channel.exchange_declare(exchange='catalog_events', exchange_type='topic', durable=True)
        channel.exchange_declare(exchange='interaction_events', exchange_type='topic', durable=True)
        channel.exchange_declare(exchange='payment_events', exchange_type='topic', durable=True)
        
        # Queues
        user_q = channel.queue_declare(queue='recommender_user_sync', durable=True)
        catalog_q = channel.queue_declare(queue='recommender_catalog_sync', durable=True)
        interaction_q = channel.queue_declare(queue='recommender_interaction_sync', durable=True)
        payment_q = channel.queue_declare(queue='recommender_payment_sync', durable=True)
        
        # Bindings
        channel.queue_bind(exchange='user_events', queue=user_q.method.queue, routing_key='user.#')
        channel.queue_bind(exchange='catalog_events', queue=catalog_q.method.queue, routing_key='catalog.#')
        channel.queue_bind(exchange='interaction_events', queue=interaction_q.method.queue, routing_key='interaction.#')
        channel.queue_bind(exchange='payment_events', queue=payment_q.method.queue, routing_key='payment.succeeded')

        self.stdout.write(self.style.SUCCESS("Waiting for recommender events..."))

        def callback(ch, method, properties, body):
            try:
                payload = json.loads(body)
                routing_key = method.routing_key
                exchange = method.exchange
                
                if exchange == 'user_events':
                    EventHandler.handle_user_event(routing_key, payload)
                elif exchange == 'catalog_events':
                    EventHandler.handle_catalog_event(routing_key, payload)
                elif exchange == 'interaction_events':
                    EventHandler.handle_interaction_event(routing_key, payload)
                elif exchange == 'payment_events':
                    EventHandler.handle_payment_event(routing_key, payload)
                    
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"Error processing {routing_key}: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_qos(prefetch_count=50)
        channel.basic_consume(queue=user_q.method.queue, on_message_callback=callback)
        channel.basic_consume(queue=catalog_q.method.queue, on_message_callback=callback)
        channel.basic_consume(queue=interaction_q.method.queue, on_message_callback=callback)
        channel.basic_consume(queue=payment_q.method.queue, on_message_callback=callback)
        
        channel.start_consuming()
