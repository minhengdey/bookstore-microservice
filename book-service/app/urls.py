from django.urls import path
from app.views import BookListCreateView, BookDetailView

urlpatterns = [
    path("books/", BookListCreateView.as_view()),
    path("books/<int:pk>/", BookDetailView.as_view()),
]
