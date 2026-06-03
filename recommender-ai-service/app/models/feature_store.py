from django.db import models
from .base import AuditBaseModel

class UserFeature(AuditBaseModel):
    user_id = models.UUIDField(primary_key=True)
    total_views = models.IntegerField(default=0)
    total_purchases = models.IntegerField(default=0)
    avg_order_value = models.FloatField(default=0.0)
    favorite_category = models.CharField(max_length=100, null=True, blank=True)
    embedding_vector = models.JSONField(null=True, blank=True) # Or pgvector if installed
    last_computed_at = models.DateTimeField(auto_now=True)

class ProductFeature(AuditBaseModel):
    product_id = models.UUIDField(primary_key=True)
    popularity_score = models.FloatField(default=0.0)
    purchase_count = models.IntegerField(default=0)
    category_embedding = models.JSONField(null=True, blank=True)
    embedding_vector = models.JSONField(null=True, blank=True)
    last_computed_at = models.DateTimeField(auto_now=True)

class InferenceCache(AuditBaseModel):
    user_id = models.UUIDField(primary_key=True)
    model_version = models.CharField(max_length=100)
    recommendations = models.JSONField() # List of product_ids
    expires_at = models.DateTimeField()

