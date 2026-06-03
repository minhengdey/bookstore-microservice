import uuid
from django.db import models

class InferenceMetric(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_version_id = models.UUIDField()
    user_id = models.UUIDField(null=True, blank=True)
    anonymous_id = models.UUIDField(null=True, blank=True)
    latency_ms = models.FloatField()
    candidate_count = models.IntegerField()
    recommendation_count = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

class RecommendationFeedback(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recommendation_id = models.UUIDField() # Ties back to a specific prediction result
    user_id = models.UUIDField(null=True, blank=True)
    product_id = models.UUIDField()
    model_version_id = models.UUIDField()
    event_type = models.CharField(max_length=30) # 'impression', 'clicked', 'purchased'
    revenue_attributed = models.FloatField(default=0.0) # Track direct revenue if purchased
    created_at = models.DateTimeField(auto_now_add=True)
