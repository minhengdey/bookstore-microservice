from django.urls import path
from .views import (
    ShippingMethodListView, ShippingListView, ShippingDetailView,
    InternalShippingCreateView, InternalShippingStatusView, ShippingCreateView,
    ShippingByOrderView, ShippingFeeCalculatorView, ShippingZoneLookupView,
)

urlpatterns = [
    path("shipping-methods/", ShippingMethodListView.as_view()),
    path("api/methods/", ShippingMethodListView.as_view()),
    path("shippings/", ShippingListView.as_view()),
    path("shippings/<int:pk>/", ShippingDetailView.as_view()),
    path("api/shippings/order/<int:order_id>/", ShippingByOrderView.as_view()),
    path("shippings/order/<int:order_id>/", ShippingByOrderView.as_view()),
    path("shipping/calculate-fee/", ShippingFeeCalculatorView.as_view()),
    path("api/shipping/calculate-fee/", ShippingFeeCalculatorView.as_view()),
    path("api/shipping/zones/", ShippingZoneLookupView.as_view()),
    path("shipping/zones/", ShippingZoneLookupView.as_view()),
    path("internal/shipping/create/", InternalShippingCreateView.as_view()),
    path("internal/shipping/status/", InternalShippingStatusView.as_view()),
    path("shipping/create/", ShippingCreateView.as_view()),
    path("shipping/status/<int:pk>/", ShippingDetailView.as_view()),
]
