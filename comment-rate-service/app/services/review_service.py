from app.repositories import ReviewRepository


class ReviewService:
    def __init__(self): self.repo = ReviewRepository()

    def list_by_book(self, book_id): return self.repo.get_by_book(book_id)
    def list_by_customer(self, customer_id): return self.repo.get_by_customer(customer_id)

    def get(self, pk):
        r = self.repo.get_by_id(pk)
        if not r: raise ValueError(f"Review {pk} not found")
        return r

    def create_review(self, data: dict):
        rating = int(data.get("rating", 0))
        if not (1 <= rating <= 5):
            raise ValueError("Rating must be between 1 and 5")
        return self.repo.create(**data)

    def update_review(self, pk, data: dict):
        review = self.get(pk)
        if "rating" in data and not (1 <= int(data["rating"]) <= 5):
            raise ValueError("Rating must be between 1 and 5")
        return self.repo.update(review, **data)

    def delete_review(self, pk):
        self.repo.delete(self.get(pk))

    def get_average_rating(self, book_id: int) -> dict:
        avg = self.repo.get_average_rating(book_id)
        count = self.repo.get_by_book(book_id).count()
        return {"book_id": book_id, "average_rating": avg, "total_reviews": count}
