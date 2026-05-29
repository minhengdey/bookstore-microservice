import os
import pika
import json
import logging
from datetime import datetime, timezone
from common.middleware import get_request_id

logger = logging.getLogger(__name__)

class EventPublisher:
    _connection = None
    _channel = None

    @classmethod
    def get_channel(cls):
        if not cls._connection or cls._connection.is_closed:
            host = os.environ.get("RABBITMQ_HOST", "rabbitmq")
            user = os.environ.get("RABBITMQ_USER", "user")
            pwd = os.environ.get("RABBITMQ_PASS", "password")
            
            credentials = pika.PlainCredentials(user, pwd)
            parameters = pika.ConnectionParameters(
                host=host, 
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            cls._connection = pika.BlockingConnection(parameters)
            cls._channel = cls._connection.channel()
            
            # Setup exchanges and DLQs globally
            cls._setup_topology()
            
        if cls._channel.is_closed:
            cls._channel = cls._connection.channel()
            
        return cls._channel

    @classmethod
    def _setup_topology(cls):
        # We enforce a DLQ topology for reliability
        channel = cls._channel
        
        # Dead Letter Exchange
        channel.exchange_declare(exchange='dlx', exchange_type='direct', durable=True)
        channel.queue_declare(queue='dlq', durable=True)
        channel.queue_bind(queue='dlq', exchange='dlx', routing_key='dlq')

        # Main Business Exchanges
        channel.exchange_declare(exchange='order_events', exchange_type='fanout', durable=True)
        channel.exchange_declare(exchange='payment_events', exchange_type='fanout', durable=True)

    @classmethod
    def publish(cls, exchange: str, event_type: str, data: dict, version: int = 1):
        """
        Publishes an event conforming to the Enterprise Event Schema:
        { "event_type", "version", "data", "trace_id", "timestamp" }
        """
        trace_id = get_request_id() or "unknown"
        
        payload = {
            "event_type": event_type,
            "version": version,
            "data": data,
            "trace_id": trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        channel = cls.get_channel()
        channel.basic_publish(
            exchange=exchange,
            routing_key="", # fanout
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=2, # Persistent
                headers={
                    "trace_id": trace_id,
                    "span": f"{os.environ.get('SERVICE_NAME', 'unknown')}->{exchange}"
                }
            )
        )
        logger.info(f"Published event {event_type} to {exchange}", extra={
            "trace_id": trace_id,
            "span": f"{os.environ.get('SERVICE_NAME', 'unknown')}->{exchange}",
            "event_type": event_type
        })

    @classmethod
    def close(cls):
        if cls._connection and not cls._connection.is_closed:
            cls._connection.close()
