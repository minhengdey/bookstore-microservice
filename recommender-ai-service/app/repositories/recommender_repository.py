from app.models import RecommendationLog, BehaviorEvent


class RecommenderRepository:
    def get_history(self, customer_id): return RecommendationLog.objects.filter(customer_id=customer_id)
    def save_log(self, customer_id, book_ids, strategy="collaborative"):
        return RecommendationLog.objects.create(customer_id=customer_id, book_ids=book_ids, strategy=strategy)

    def save_behavior(self, customer_id, book_id, action, action_weight=1.0):
        return BehaviorEvent.objects.create(
            customer_id=customer_id,
            book_id=book_id,
            action=action,
            action_weight=action_weight,
        )

    def get_behavior_scores(self, customer_id):
        events = BehaviorEvent.objects.filter(customer_id=customer_id).values(
            "book_id", "action", "action_weight"
        )
        scores = {}
        for ev in events:
            book_id = ev["book_id"]
            weight = float(ev.get("action_weight") or 1.0)
            scores[book_id] = scores.get(book_id, 0.0) + weight
        return scores
