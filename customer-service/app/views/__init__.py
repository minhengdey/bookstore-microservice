from .customer_views import CustomerListCreateView, CustomerDetailView
from .address_views import AddressListCreateView, AddressDetailView
from .auth_views import (
    CustomerLoginView,
    CustomerTokenRefreshView,
    CustomerRegisterView,
    CustomerMeView,
)

__all__ = [
    "CustomerListCreateView", "CustomerDetailView",
    "AddressListCreateView", "AddressDetailView",
    "CustomerLoginView", "CustomerTokenRefreshView",
    "CustomerRegisterView", "CustomerMeView",
]
