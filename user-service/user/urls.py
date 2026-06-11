from django.urls import path
from .views import (
    UserProfileView, PublicUserProfileView, AddressListView, AddressDetailView,
    CustomerListView, CustomerDetailView,
)

urlpatterns = [
    path("internal/customers/", CustomerListView.as_view(), name="internal-customers"),
    path("internal/customers/<int:customer_id>/", CustomerDetailView.as_view(), name="internal-customer-detail"),
    path("internal/users/", UserProfileView.as_view(), name="internal-users"),
    path("internal/users/<uuid:user_id>/", UserProfileView.as_view(), name="internal-user-profile"),
    path("internal/users/<uuid:user_id>/addresses/", AddressListView.as_view(), name="internal-user-addresses"),
    path("internal/users/<uuid:user_id>/addresses/<int:address_id>/", AddressDetailView.as_view(), name="internal-user-address-detail"),
    path("api/users/me/", UserProfileView.as_view(), name="user-profile-legacy"),
    path("users/me/", PublicUserProfileView.as_view(), name="user-profile-public"),
]
