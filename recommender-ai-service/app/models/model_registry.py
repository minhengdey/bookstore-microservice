from django.db import models
from .base import AuditBaseModel

class ModelVersion(AuditBaseModel):
    model_name = models.CharField(max_length=100)
    version = models.IntegerField()
    framework = models.CharField(max_length=20, choices=[('PYTORCH', 'PYTORCH'), ('TENSORFLOW', 'TENSORFLOW')])
    model_type = models.CharField(max_length=50, choices=[('BILSTM', 'BILSTM'), ('LIGHTGCN', 'LIGHTGCN'), ('NCF', 'NCF')])
    path = models.CharField(max_length=255) # Path to weights
    metric_name = models.CharField(max_length=50)
    metric_value = models.FloatField()
    
    # Advanced MLOps Metadata
    artifact_hash = models.CharField(max_length=255, null=True, blank=True)
    artifact_size = models.BigIntegerField(null=True, blank=True)
    training_dataset_version = models.CharField(max_length=100, null=True, blank=True)
    feature_schema_version = models.CharField(max_length=100, null=True, blank=True)
    
    rollout_percentage = models.IntegerField(default=100)
    deployed_at = models.DateTimeField(null=True, blank=True)
    rollback_target = models.UUIDField(null=True, blank=True)
    
    # Baseline tracking for Drift Detection
    baseline_distribution = models.JSONField(null=True, blank=True) # e.g. {"Electronics": 0.42, "Books": 0.18}
    baseline_sample_size = models.IntegerField(null=True, blank=True)
    baseline_period_start = models.DateTimeField(null=True, blank=True)
    baseline_period_end = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(
        max_length=20, 
        choices=[
            ('TRAINING', 'TRAINING'), 
            ('VALIDATING', 'VALIDATING'), 
            ('ACTIVE', 'ACTIVE'), 
            ('ROLLED_BACK', 'ROLLED_BACK'), 
            ('DEPRECATED', 'DEPRECATED')
        ],
        default='TRAINING'
    )

class ModelMetric(AuditBaseModel):
    model_version = models.ForeignKey(ModelVersion, on_delete=models.CASCADE, related_name='metrics')
    ctr = models.FloatField(default=0.0)
    add_to_cart_rate = models.FloatField(default=0.0)
    purchase_rate = models.FloatField(default=0.0)
    ndcg = models.FloatField(default=0.0)
    evaluated_at = models.DateTimeField(auto_now_add=True)
