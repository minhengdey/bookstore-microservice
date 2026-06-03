from django.contrib import admin
from django.urls import path, include
from catalog.views.health import health_check, ready_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health', health_check),
    path('ready', ready_check),
    path('api/v1/catalog/', include('catalog.urls')),
]
