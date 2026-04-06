from django.urls import path
from app.views import (
    CustomerListCreateView, CustomerDetailView,
    AddressListCreateView, AddressDetailView,
    CustomerLoginView, CustomerTokenRefreshView,
    CustomerRegisterView, CustomerMeView,
)
from app.views.metrics_views import CustomerMetricsView

urlpatterns = [
    # ── Auth endpoints ────────────────────────────────────────────────────────
    path("auth/login/",    CustomerLoginView.as_view()),
    path("auth/register/", CustomerRegisterView.as_view()),
    path("auth/refresh/",  CustomerTokenRefreshView.as_view()),
    path("auth/me/",       CustomerMeView.as_view()),

    # ── Customer CRUD ─────────────────────────────────────────────────────────
    path("customers/",                                         CustomerListCreateView.as_view()),
    path("customers/<int:pk>/",                                CustomerDetailView.as_view()),
    path("customers/<int:customer_id>/addresses/",             AddressListCreateView.as_view()),
    path("customers/<int:customer_id>/addresses/<int:pk>/",    AddressDetailView.as_view()),
    
    # ── Internal Service Metrics ──────────────────────────────────────────────
    path("customers/metrics/",                                 CustomerMetricsView.as_view()),
]
