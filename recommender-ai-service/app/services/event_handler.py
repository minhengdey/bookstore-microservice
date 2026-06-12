import json
import logging
import redis
import os
from datetime import datetime
from django.db import transaction
from django.utils import timezone
from app.models import UserProjection, ProductProjection, UserSequenceEvent
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

# Redis Connection
redis_url = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
redis_client = redis.from_url(redis_url)

# Neo4j Connection
neo4j_uri = os.environ.get('NEO4J_URI', 'bolt://neo4j:7687')
neo4j_user = os.environ.get('NEO4J_USER', 'neo4j')
neo4j_password = os.environ.get('NEO4J_PASSWORD', 'password123')
try:
    neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
except Exception as e:
    logger.warning(f"Could not connect to Neo4j: {e}")
    neo4j_driver = None

class EventHandler:
    
    @staticmethod
    def handle_user_event(routing_key: str, payload: dict):
        # Handle user.created or user.updated
        user_id = payload.get('id') or payload.get('user_id')
        event_version = payload.get('event_version', 1)
        if not user_id:
            return
            
        with transaction.atomic():
            user, created = UserProjection.objects.get_or_create(user_id=user_id)
            if not created and user.projection_version >= event_version:
                return # Out of order event
                
            if 'role' in payload:
                user.role = payload['role']
            if 'is_active' in payload:
                user.is_active = payload['is_active']
                
            user.projection_version = event_version
            user.save()
            logger.info(f"Updated UserProjection {user_id}")

    @staticmethod
    def handle_catalog_event(routing_key: str, payload: dict):
        # Handle catalog.product.created or updated
        product_id = payload.get('id') or payload.get('product_id')
        event_version = payload.get('event_version', 1)
        if not product_id:
            return
            
        with transaction.atomic():
            product, created = ProductProjection.objects.get_or_create(product_id=product_id)
            if not created and product.projection_version >= event_version:
                return # Out of order event
                
            if 'category_id' in payload:
                product.category_id = payload['category_id']
            if 'brand_id' in payload:
                product.brand_id = payload['brand_id']
            if 'name' in payload:
                product.name = payload['name']
            if 'slug' in payload:
                product.slug = payload['slug']
            if 'is_active' in payload:
                product.is_active = payload['is_active']
                
            product.projection_version = event_version
            product.save()
            logger.info(f"Updated ProductProjection {product_id}")

    @staticmethod
    def handle_interaction_event(routing_key: str, payload: dict):
        user_id = payload.get('user_id')
        product_id = payload.get('product_id')
        event_type = payload.get('event_type', '').split('.')[-1].upper() # interaction.view -> VIEW
        weight = float(payload.get('weight', 1.0))
        occurred_at = payload.get('occurred_at')
        
        # Security: Do not allow PURCHASE events from raw interaction stream
        if event_type == 'PURCHASE':
            logger.warning("Dropped raw PURCHASE interaction event. Must come from payment.")
            return
            
        if not user_id or not product_id:
            return
            
        EventHandler._process_interaction(user_id, product_id, event_type, weight, occurred_at)

    @staticmethod
    def handle_payment_event(routing_key: str, payload: dict):
        # payment.succeeded triggers the PURCHASE interaction
        if routing_key == 'payment.succeeded':
            user_id = payload.get('user_id')
            occurred_at = payload.get('occurred_at')
            
            # Since a payment can cover multiple order items, we'd ideally fetch them or have them in payload.
            # Assuming payload contains product_ids or we have to query.
            # For simplicity, if payload has product_id, use it. Otherwise, this is a stub.
            product_id = payload.get('product_id')
            
            if user_id and product_id:
                EventHandler._process_interaction(user_id, product_id, 'PURCHASE', 10.0, occurred_at)

    @staticmethod
    def _process_interaction(user_id: str, product_id: str, event_type: str, weight: float, occurred_at: str = None):
        from app.services.behavior_sync import record_behavior_from_interaction

        record_behavior_from_interaction(
            user_id=user_id,
            product_id=product_id,
            event_type=event_type,
            weight=weight,
        )

        # 1. Store backup in PostgreSQL
        ts = datetime.fromisoformat(occurred_at) if occurred_at else timezone.now()
        UserSequenceEvent.objects.create(
            user_id=user_id, product_id=product_id, event_type=event_type, weight=weight, timestamp=ts
        )
        
        # 2. Update Redis Sequence Store (BiLSTM context)
        EventHandler._update_redis_sequence(user_id, product_id, event_type, weight)
        
        # 3. Update Redis Trending (Time-binned)
        if event_type in ['VIEW', 'PURCHASE', 'ADD_TO_CART']:
            EventHandler._update_redis_trending(product_id, weight)
            
        # 4. Update Neo4j Graph
        if neo4j_driver:
            EventHandler._update_neo4j_graph(user_id, product_id, event_type, weight)
            
    @staticmethod
    def _update_redis_sequence(user_id: str, product_id: str, event_type: str, weight: float):
        key = f"user_sequence:{user_id}"
        event_obj = json.dumps({
            "product_id": product_id,
            "event_type": event_type,
            "weight": weight,
            "timestamp": timezone.now().isoformat()
        })
        
        pipe = redis_client.pipeline()
        pipe.lpush(key, event_obj)
        pipe.ltrim(key, 0, 99) # Keep last 100 interactions
        pipe.execute()
        
    @staticmethod
    def _update_redis_trending(product_id: str, weight: float):
        # Maintain an hourly trending window for the last 24h
        current_hour = timezone.now().strftime('%Y-%m-%d:%H')
        trending_key = f"trending:{current_hour}"
        redis_client.zincrby(trending_key, weight, product_id)
        redis_client.expire(trending_key, 86400 * 2) # Expire in 48h

    @staticmethod
    def _update_neo4j_graph(user_id: str, product_id: str, event_type: str, weight: float):
        # We map events to specific edges
        edge_type = event_type
        if edge_type == 'ADD_TO_CART':
            edge_type = 'ADDED_TO_CART'
            
        cypher = f"""
        MERGE (u:User {{id: $user_id}})
        MERGE (p:Product {{id: $product_id}})
        MERGE (u)-[r:{edge_type}]->(p)
        SET r.weight = coalesce(r.weight, 0) + $weight,
            r.last_interaction = datetime(),
            r.interaction_count = coalesce(r.interaction_count, 0) + 1
        """
        
        try:
            with neo4j_driver.session() as session:
                session.run(cypher, user_id=user_id, product_id=product_id, weight=weight)
        except Exception as e:
            logger.error(f"Neo4j Error: {e}")
