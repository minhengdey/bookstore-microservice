from django.urls import path
from .views import ProductListView, ProductDetailView, CategoryListView, InternalReserveStockView, InternalReleaseStockView

urlpatterns = [
    path("products/", ProductListView.as_view()),
    path("products/<int:pk>/", ProductDetailView.as_view()),
    path("categories/", CategoryListView.as_view()),
    path("internal/reserve-stock/", InternalReserveStockView.as_view()),
    path("internal/release-stock/", InternalReleaseStockView.as_view()),
]
