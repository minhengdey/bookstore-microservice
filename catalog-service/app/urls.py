from django.urls import path
from app.views import (
    AuthorListCreateView, AuthorDetailView,
    CategoryListCreateView, CategoryDetailView,
    GenreListCreateView, GenreDetailView,
    PublisherListCreateView, PublisherDetailView,
)

urlpatterns = [
    path("authors/", AuthorListCreateView.as_view()),
    path("authors/<int:pk>/", AuthorDetailView.as_view()),
    path("categories/", CategoryListCreateView.as_view()),
    path("categories/<int:pk>/", CategoryDetailView.as_view()),
    path("genres/", GenreListCreateView.as_view()),
    path("genres/<int:pk>/", GenreDetailView.as_view()),
    path("publishers/", PublisherListCreateView.as_view()),
    path("publishers/<int:pk>/", PublisherDetailView.as_view()),
]
