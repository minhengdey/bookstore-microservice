from app.models import RecommendationLog


class RecommenderRepository:
    def get_history(self, customer_id): return RecommendationLog.objects.filter(customer_id=customer_id)
    def save_log(self, customer_id, book_ids, strategy="collaborative"):
        return RecommendationLog.objects.create(customer_id=customer_id, book_ids=book_ids, strategy=strategy)
