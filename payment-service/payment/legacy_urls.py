from django.urls import path
from .legacy_views import PaymentMethodListView, PaymentListCreateView, PaymentDetailView, RefundView, InternalPaymentView

urlpatterns = [
    path('payment-methods/', PaymentMethodListView.as_view(), name='payment-methods'),
    path('payments/', PaymentListCreateView.as_view(), name='payments'),
    path('payments/<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),
    path('payments/<int:payment_id>/refund/', RefundView.as_view(), name='payment-refund'),
    path('internal/payments/', InternalPaymentView.as_view(), name='internal-payments'),
]
