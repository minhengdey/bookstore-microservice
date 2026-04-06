from django.urls import path
from app.views import OrderListCreateView, OrderDetailView, DiscountListCreateView
from app.views.metrics_views import OrderMetricsView

urlpatterns = [
    path("orders/", OrderListCreateView.as_view()),
    path("orders/<int:pk>/", OrderDetailView.as_view()),
    path("discounts/", DiscountListCreateView.as_view()),
    
    # ── Internal Service Metrics ──────────────────────────────────────────────
    path("orders/metrics/", OrderMetricsView.as_view()),
]
