import json
import logging
import math
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from app.models import ModelVersion, ProductProjection, UserSequenceEvent
from app.services.event_handler import publish_event

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Monitors active models for data drift (PSI) and triggers retraining if necessary'

    def handle(self, *args, **options):
        active_models = ModelVersion.objects.filter(status='ACTIVE').exclude(baseline_distribution__isnull=True)
        
        for model in active_models:
            self.stdout.write(f"Checking drift for {model.model_name}_v{model.version}...")
            
            # 1. Get baseline
            baseline = model.baseline_distribution
            if not baseline:
                continue
                
            # 2. Get live distribution (last 24 hours of views from Sequence Events)
            cutoff = timezone.now() - timedelta(hours=24)
            recent_events = UserSequenceEvent.objects.filter(timestamp__gte=cutoff, event_type='VIEW')
            
            # Count categories
            category_counts = {}
            total_events = 0
            
            # We need to join with ProductProjection to get the category
            product_ids = [e.product_id for e in recent_events]
            products = ProductProjection.objects.in_bulk(product_ids)
            
            for event in recent_events:
                prod = products.get(event.product_id)
                if prod and prod.category_id:
                    cat_id = str(prod.category_id)
                    category_counts[cat_id] = category_counts.get(cat_id, 0) + 1
                    total_events += 1
                    
            if total_events == 0:
                self.stdout.write("No events in last 24h, skipping.")
                continue
                
            # Normalize live distribution
            live_dist = {cat: count / total_events for cat, count in category_counts.items()}
            
            # 3. Calculate PSI (Population Stability Index)
            psi = 0.0
            
            # Ensure we compare all keys present in either distribution
            all_keys = set(baseline.keys()).union(set(live_dist.keys()))
            
            for cat in all_keys:
                # Add a tiny epsilon to avoid division by zero or log(0)
                epsilon = 0.0001
                base_val = baseline.get(cat, 0) + epsilon
                live_val = live_dist.get(cat, 0) + epsilon
                
                # PSI Formula: sum((Actual% - Expected%) * ln(Actual% / Expected%))
                psi += (live_val - base_val) * math.log(live_val / base_val)
                
            self.stdout.write(f"PSI for {model.model_name}_v{model.version} = {psi:.4f}")
            
            # 4. Trigger Retraining if Drift > 0.25
            if psi > 0.25:
                logger.warning(f"SEVERE DRIFT DETECTED (PSI={psi:.4f}) for {model.model_name}_v{model.version}. Triggering retrain.")
                
                payload = {
                    "model_name": model.model_name,
                    "current_version": model.version,
                    "psi_score": psi,
                    "trigger": "DRIFT_DETECTED",
                    "timestamp": timezone.now().isoformat()
                }
                
                publish_event('recommendation_events', 'model.retrain.requested', payload)
