from django.urls import path
from .views import PaymentListCreateView, PaymentDetailView, PaymentMethodListView, RefundView, InternalPaymentView

urlpatterns = [
    path("payment-methods/", PaymentMethodListView.as_view()),
    path("payments/", PaymentListCreateView.as_view()),
    path("payments/<int:pk>/", PaymentDetailView.as_view()),
    path("payments/<int:payment_id>/refund/", RefundView.as_view()),
    path("internal/pay/", InternalPaymentView.as_view()),
    
    # Alias endpoints to match spec
    path("payment/pay/", PaymentListCreateView.as_view()),
    path("payment/status/<int:pk>/", PaymentDetailView.as_view()),
]
