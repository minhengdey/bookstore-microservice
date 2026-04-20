from django.urls import path
from .views.product_view import ProductListCreateAPI, ProductDetailAPI

urlpatterns = [
    # Book compatibility
    path("books/", ProductListCreateAPI.as_view(), name="product-list"),
    path("books/<int:product_id>/", ProductDetailAPI.as_view(), name="product-detail"),
    
    # Legacy PK compatibility
    path("books/<int:pk>/", ProductDetailAPI.as_view(), name="product-detail-pk"),
]
