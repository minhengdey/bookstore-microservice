import requests, logging
from collections import Counter
from app.repositories import RecommenderRepository

logger = logging.getLogger(__name__)

ORDER_SERVICE_URL = "http://order-service:8000"
BOOK_SERVICE_URL = "http://book-service:8000"
COMMENT_RATE_URL = "http://comment-rate-service:8000"


class RecommenderService:
    """
    Collaborative-filtering recommendation strategy:
    1. Fetch books customer has ordered
    2. Find other customers who ordered the same books
    3. Recommend books those customers also bought (that this customer hasn't)
    """

    def __init__(self):
        self.repo = RecommenderRepository()

    def recommend(self, customer_id: int, limit: int = 10) -> list:
        # Step 1: books this customer already ordered
        customer_books = self._get_customer_books(customer_id)

        # Step 2: get all orders, find co-buyers
        all_orders = self._get_all_orders()
        co_buyer_books = Counter()
        for order in all_orders:
            if order.get("customer_id") == customer_id:
                continue
            items = order.get("items", [])
            order_book_ids = [i["book_id"] for i in items]
            if any(bid in customer_books for bid in order_book_ids):
                for bid in order_book_ids:
                    if bid not in customer_books:
                        co_buyer_books[bid] += 1

        # Step 3: top recommendations + highly-rated books fallback
        recommended = [bid for bid, _ in co_buyer_books.most_common(limit)]

        if len(recommended) < limit:
            top_rated = self._get_top_rated_books(limit)
            for bid in top_rated:
                if bid not in customer_books and bid not in recommended:
                    recommended.append(bid)
                if len(recommended) >= limit:
                    break

        self.repo.save_log(customer_id, recommended[:limit])
        return recommended[:limit]

    def _get_customer_books(self, customer_id: int) -> set:
        try:
            r = requests.get(f"{ORDER_SERVICE_URL}/orders/?customer_id={customer_id}", timeout=5)
            if r.status_code == 200:
                return {item["book_id"] for order in r.json() for item in order.get("items", [])}
        except requests.exceptions.RequestException as e:
            logger.warning(f"order-service unreachable: {e}")
        return set()

    def _get_all_orders(self) -> list:
        try:
            r = requests.get(f"{ORDER_SERVICE_URL}/orders/", timeout=5)
            if r.status_code == 200:
                return r.json().get("results", r.json()) if isinstance(r.json(), dict) else r.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"order-service unreachable: {e}")
        return []

    def _get_top_rated_books(self, limit: int) -> list:
        try:
            r = requests.get(f"{BOOK_SERVICE_URL}/books/", timeout=5)
            if r.status_code == 200:
                books = r.json().get("results", r.json()) if isinstance(r.json(), dict) else r.json()
                return [b["id"] for b in books[:limit]]
        except requests.exceptions.RequestException:
            pass
        return []
