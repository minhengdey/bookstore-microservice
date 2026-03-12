from django.urls import path
from app.views import CartView, CartItemView, CartItemDetailView

urlpatterns = [
    path("carts/", CartView.as_view()),
    path("carts/<int:customer_id>/", CartView.as_view()),
    path("carts/<int:customer_id>/items/", CartItemView.as_view()),
    path("carts/<int:customer_id>/items/<int:item_id>/", CartItemDetailView.as_view()),
]
