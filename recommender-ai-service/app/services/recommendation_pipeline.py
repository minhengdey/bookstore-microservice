import os
import json
import logging
import requests
import time
import hashlib
from datetime import timedelta
from django.utils import timezone
from app.models import InferenceCache, UserFeature, ProductFeature, ProductProjection, ModelVersion, InferenceMetric
from app.services.event_handler import redis_client, neo4j_driver

logger = logging.getLogger(__name__)

MODEL_SERVING_URL = os.environ.get('MODEL_SERVING_URL', 'http://model-serving-service:8000')

class RecommendationPipeline:

    @staticmethod
    def _get_active_model(user_id: str) -> ModelVersion:
        active_models = list(ModelVersion.objects.filter(status='ACTIVE').order_by('-version'))
        if not active_models:
            return None
            
        if len(active_models) == 1:
            return active_models[0]
            
        # A/B Testing Routing using stable MD5 hash
        uid_str = str(user_id) if user_id else "anonymous"
        bucket = int(hashlib.md5(uid_str.encode()).hexdigest(), 16) % 100
        
        cumulative_pct = 0
        for model in active_models:
            cumulative_pct += model.rollout_percentage
            if bucket < cumulative_pct:
                return model
                
        return active_models[0] # Fallback

    @staticmethod
    def get_personal_recommendations(user_id: str, limit: int = 10) -> dict:
        start_time = time.time()
        
        # 1. Determine Model Version
        active_model = RecommendationPipeline._get_active_model(user_id)
        model_ver_str = f"{active_model.model_name}_v{active_model.version}" if active_model else "fallback_v1"
        model_ver_id = str(active_model.id) if active_model else None
        
        # 2. Check Inference Cache
        cached = InferenceCache.objects.filter(user_id=user_id, model_version=model_ver_str, expires_at__gt=timezone.now()).first()
        if cached:
            logger.info("Serving recommendations from InferenceCache")
            recs = RecommendationPipeline._hydrate_products(cached.recommendations[:limit])
            RecommendationPipeline._record_metric(user_id, model_ver_id, start_time, len(cached.recommendations), len(recs))
            return {"model_version": model_ver_str, "recommendations": recs, "recommendation_id": str(cached.id)}
            
        # 3. Candidate Retrieval (Neo4j Graph walk)
        candidates = RecommendationPipeline._retrieve_candidates_neo4j(user_id)
        if not candidates:
            # Fallback to trending
            candidates = RecommendationPipeline._get_trending_ids(limit=50)
            
        # 3. Retrieve Sequence context from Redis
        sequence_data = redis_client.lrange(f"user_sequence:{user_id}", 0, 99)
        sequence = [json.loads(x) for x in sequence_data]
        
        # 5. Call Model Serving Service
        try:
            payload = {
                "model_version": model_ver_str,
                "user_id": str(user_id),
                "sequence": sequence,
                "candidates": candidates
            }
            resp = requests.post(f"{MODEL_SERVING_URL}/predict", json=payload, timeout=2.0)
            resp.raise_for_status()
            inference_result = resp.json()
            sorted_product_ids = inference_result.get('recommendations', [])
            
            # 6. Save to Cache (5 minutes TTL)
            cache_obj, _ = InferenceCache.objects.update_or_create(
                user_id=user_id,
                model_version=model_ver_str,
                defaults={
                    'recommendations': sorted_product_ids,
                    'expires_at': timezone.now() + timedelta(minutes=5)
                }
            )
            
            recs = RecommendationPipeline._hydrate_products(sorted_product_ids[:limit])
            RecommendationPipeline._record_metric(user_id, model_ver_id, start_time, len(candidates), len(recs))
            
            return {"model_version": model_ver_str, "recommendations": recs, "recommendation_id": str(cache_obj.id)}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Model Serving failed: {e}")
            # Fallback to pure candidates
            recs = RecommendationPipeline._hydrate_products(candidates[:limit])
            RecommendationPipeline._record_metric(user_id, model_ver_id, start_time, len(candidates), len(recs))
            return {"model_version": "fallback", "recommendations": recs, "recommendation_id": None}

    @staticmethod
    def _record_metric(user_id, model_ver_id, start_time, candidate_count, rec_count):
        latency_ms = (time.time() - start_time) * 1000
        if model_ver_id:
            InferenceMetric.objects.create(
                model_version_id=model_ver_id,
                user_id=user_id,
                latency_ms=latency_ms,
                candidate_count=candidate_count,
                recommendation_count=rec_count
            )

    @staticmethod
    def _retrieve_candidates_neo4j(user_id: str) -> list:
        if not neo4j_driver:
            return []
            
        # Collaborative filtering via Graph: "Users who bought what you bought also bought..."
        cypher = """
        MATCH (u:User {id: $user_id})-[:PURCHASED|ADDED_TO_CART]->(p:Product)<-[:PURCHASED|ADDED_TO_CART]-(other:User)-[:PURCHASED]->(rec:Product)
        WHERE NOT (u)-[:PURCHASED]->(rec)
        RETURN rec.id as product_id, count(*) as score
        ORDER BY score DESC
        LIMIT 100
        """
        candidates = []
        try:
            with neo4j_driver.session() as session:
                result = session.run(cypher, user_id=user_id)
                for record in result:
                    candidates.append(record["product_id"])
        except Exception as e:
            logger.error(f"Neo4j Candidate Retrieval Error: {e}")
            
        return candidates

    @staticmethod
    def _get_trending_ids(limit: int = 50) -> list:
        current_hour = timezone.now().strftime('%Y-%m-%d:%H')
        trending_key = f"trending:{current_hour}"
        items = redis_client.zrevrange(trending_key, 0, limit - 1)
        return [item.decode('utf-8') for item in items]
        
    @staticmethod
    def get_trending_recommendations(limit: int = 10) -> list:
        ids = RecommendationPipeline._get_trending_ids(limit)
        return RecommendationPipeline._hydrate_products(ids)

    @staticmethod
    def _hydrate_products(product_ids: list) -> list:
        # Fetch metadata from local ProductProjection
        projections = ProductProjection.objects.in_bulk(product_ids)
        result = []
        for pid in product_ids:
            # PID might be string or UUID, try both
            p = projections.get(pid)
            if not p:
                import uuid
                try:
                    p = projections.get(uuid.UUID(pid))
                except:
                    pass
            if p and p.is_active:
                result.append({
                    "product_id": str(p.product_id),
                    "name": p.name,
                    "slug": p.slug,
                    "category_id": str(p.category_id) if p.category_id else None
                })
        return result
