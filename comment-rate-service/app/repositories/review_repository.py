from django.db.models import Avg
from app.models import BookReview


class ReviewRepository:
    def get_all(self): return BookReview.objects.all()
    def get_by_id(self, pk): return BookReview.objects.filter(pk=pk).first()
    def get_by_book(self, book_id): return BookReview.objects.filter(book_id=book_id, status="approved")
    def get_by_customer(self, customer_id): return BookReview.objects.filter(customer_id=customer_id)
    def get_average_rating(self, book_id) -> float:
        result = BookReview.objects.filter(book_id=book_id, status="approved").aggregate(avg=Avg("rating"))
        return round(result["avg"] or 0, 2)
    def create(self, **kw): return BookReview.objects.create(**kw)
    def update(self, review, **kw):
        for k, v in kw.items(): setattr(review, k, v)
        review.save(); return review
    def delete(self, review): review.delete()
