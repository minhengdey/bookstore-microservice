from django.urls import path
from .views import (
    CartAddView,
    CartDetailView,
    CartItemView,
    CartItemsView,
    CartView,
    CustomerCartItemView,
    InternalCartView,
)

urlpatterns = [
    path("carts/<int:customer_id>/", CartDetailView.as_view()),
    path("carts/<int:customer_id>/items/", CartItemsView.as_view()),
    path("carts/<int:customer_id>/items/<int:item_id>/", CustomerCartItemView.as_view()),
    path("cart/", CartView.as_view()),
    path("cart/add/", CartAddView.as_view()),
    path("cart/items/<int:item_id>/", CartItemView.as_view()),
    path("internal/cart/<int:customer_id>/", InternalCartView.as_view()),
]
