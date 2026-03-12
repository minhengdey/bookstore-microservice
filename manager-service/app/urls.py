from django.urls import path
from app.views import (
    WarehouseListCreateView, WarehouseDetailView,
    InventoryListCreateView,
    SupplierListCreateView, SupplierDetailView,
    PurchaseOrderListCreateView, PurchaseOrderDetailView,
)

urlpatterns = [
    path("warehouses/", WarehouseListCreateView.as_view()),
    path("warehouses/<int:pk>/", WarehouseDetailView.as_view()),
    path("inventory/", InventoryListCreateView.as_view()),
    path("suppliers/", SupplierListCreateView.as_view()),
    path("suppliers/<int:pk>/", SupplierDetailView.as_view()),
    path("purchase-orders/", PurchaseOrderListCreateView.as_view()),
    path("purchase-orders/<int:pk>/", PurchaseOrderDetailView.as_view()),
]
