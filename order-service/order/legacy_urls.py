from django.urls import path
from .legacy_views import OrderListCreateView, OrderDetailView, OrderMetricsView, InternalBulkOrderStatusView

urlpatterns = [
    path('metrics/', OrderMetricsView.as_view(), name='legacy-order-metrics'),
    path('internal/bulk-status/', InternalBulkOrderStatusView.as_view(), name='legacy-internal-bulk-status'),
    path('<int:pk>/', OrderDetailView.as_view(), name='legacy-order-detail'),
    path('', OrderListCreateView.as_view(), name='legacy-order-list-create'),
]
