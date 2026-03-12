from django.urls import path
from app.views import OrderListCreateView, OrderDetailView, DiscountListCreateView

urlpatterns = [
    path("orders/", OrderListCreateView.as_view()),
    path("orders/<int:pk>/", OrderDetailView.as_view()),
    path("discounts/", DiscountListCreateView.as_view()),
]
