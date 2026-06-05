from django.contrib import admin
from django.urls import path, include
from order.views.health import health_check, ready_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health', health_check),
    path('ready', ready_check),
    path('api/v1/orders/', include('order.urls')),
    path('orders/', include('order.legacy_urls')),
]
