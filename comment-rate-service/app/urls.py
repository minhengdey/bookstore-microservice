from django.urls import path
from app.views import BookReviewView, BookRatingView, ReviewDetailView

urlpatterns = [
    path("reviews/", BookReviewView.as_view()),
    path("reviews/<int:pk>/", ReviewDetailView.as_view()),
    path("books/<int:book_id>/rating/", BookRatingView.as_view()),
]
