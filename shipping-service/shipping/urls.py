from django.urls import path
from .views import ShippingMethodListView, ShippingListView, ShippingDetailView, InternalShippingCreateView, ShippingCreateView

urlpatterns = [
    path("shipping-methods/", ShippingMethodListView.as_view()),
    path("shippings/", ShippingListView.as_view()),
    path("shippings/<int:pk>/", ShippingDetailView.as_view()),
    path("internal/shipping/create/", InternalShippingCreateView.as_view()),
    
    # Alias endpoints to match spec
    path("shipping/create/", ShippingCreateView.as_view()),
    path("shipping/status/<int:pk>/", ShippingDetailView.as_view()),
]
