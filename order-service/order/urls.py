from django.urls import path
from .views import OrderListCreateView, OrderDetailView, DiscountListCreateView, OrderMetricsView, InternalBulkOrderStatusView

urlpatterns = [
    path("orders/", OrderListCreateView.as_view()),
    path("orders/<int:pk>/", OrderDetailView.as_view()),
    path("discounts/", DiscountListCreateView.as_view()),
    
    # ── Internal Service Metrics ──────────────────────────────────────────────
    path("orders/metrics/", OrderMetricsView.as_view()),
    
    # ── Internal APIs ──────────────────────────────────────────────
    path("internal/orders/bulk-status/", InternalBulkOrderStatusView.as_view()),
]
