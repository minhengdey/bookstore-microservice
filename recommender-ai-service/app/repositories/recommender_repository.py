from app.models import RecommendationLog, BehaviorEvent


class RecommenderRepository:
    def get_history(self, customer_id): return RecommendationLog.objects.filter(customer_id=customer_id)
    def save_log(self, customer_id, product_ids, strategy="collaborative"):
        return RecommendationLog.objects.create(customer_id=customer_id, product_ids=product_ids, strategy=strategy)

    def save_behavior(self, customer_id, product_id, action, action_weight=1.0, **kwargs):
        return BehaviorEvent.objects.create(
            customer_id=customer_id,
            product_id=product_id,
            action=action,
            action_weight=action_weight,
            **kwargs
        )

    def get_behavior_scores(self, customer_id):
        events = BehaviorEvent.objects.filter(customer_id=customer_id).values(
            "product_id", "action", "action_weight"
        )
        scores = {}
        for ev in events:
            pid = ev["product_id"]
            weight = float(ev.get("action_weight") or 1.0)
            scores[pid] = scores.get(pid, 0.0) + weight
        return scores
