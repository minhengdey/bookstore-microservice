from django.urls import path
from .legacy_views import (
    OrderListCreateView, OrderDetailView, OrderMetricsView,
    InternalBulkOrderStatusView, InternalOrderMarkPaidView,
    InternalRecommenderOrdersView,
    StaffBulkOrderUpdateView, OrderReturnRequestView,
)

urlpatterns = [
    path('internal/recommender-orders/', InternalRecommenderOrdersView.as_view(), name='legacy-internal-recommender-orders'),
    path('metrics/', OrderMetricsView.as_view(), name='legacy-order-metrics'),
    path('bulk-update/', StaffBulkOrderUpdateView.as_view(), name='legacy-staff-bulk-update'),
    path('internal/bulk-status/', InternalBulkOrderStatusView.as_view(), name='legacy-internal-bulk-status'),
    path('internal/<int:pk>/mark-paid/', InternalOrderMarkPaidView.as_view(), name='legacy-internal-mark-paid'),
    path('<int:pk>/return/', OrderReturnRequestView.as_view(), name='legacy-order-return'),
    path('<int:pk>/', OrderDetailView.as_view(), name='legacy-order-detail'),
    path('', OrderListCreateView.as_view(), name='legacy-order-list-create'),
]
