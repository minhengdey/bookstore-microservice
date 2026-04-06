from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", include("gateway.urls")),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
