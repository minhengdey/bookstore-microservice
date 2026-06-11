from django.urls import path
from .views import (
    ProductListView, ProductDetailView, 
    CategoryListView, CategoryDetailView,
    BrandListView, BrandDetailView,
    ProductVariantListView, ProductVariantDetailView,
    InternalReserveStockView, InternalReleaseStockView,
    InventoryTransactionListView
)

urlpatterns = [
    path("products/", ProductListView.as_view()),
    path("products/<int:pk>/", ProductDetailView.as_view()),
    path("categories/", CategoryListView.as_view()),
    path("categories/<int:pk>/", CategoryDetailView.as_view()),
    path("brands/", BrandListView.as_view()),
    path("brands/<int:pk>/", BrandDetailView.as_view()),
    path("variants/", ProductVariantListView.as_view()),
    path("variants/<int:pk>/", ProductVariantDetailView.as_view()),
    path("inventory-transactions/", InventoryTransactionListView.as_view()),
    path("internal/reserve-stock/", InternalReserveStockView.as_view()),
    path("internal/release-stock/", InternalReleaseStockView.as_view()),
]
