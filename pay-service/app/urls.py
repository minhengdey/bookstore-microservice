from django.urls import path
from app.views import PaymentListCreateView, PaymentDetailView, PaymentMethodListView, RefundView

urlpatterns = [
    path("payment-methods/", PaymentMethodListView.as_view()),
    path("payments/", PaymentListCreateView.as_view()),
    path("payments/<int:pk>/", PaymentDetailView.as_view()),
    path("payments/<int:payment_id>/refund/", RefundView.as_view()),
]
