from django.urls import path
from app.views import ShippingListCreateView, ShippingDetailView, ShippingMethodListView

urlpatterns = [
    path("shipping-methods/", ShippingMethodListView.as_view()),
    path("shippings/", ShippingListCreateView.as_view()),
    path("shippings/<int:pk>/", ShippingDetailView.as_view()),
]
