from django.urls import path, include

urlpatterns = [
    # Match existing service URL patterns for compatibility with API Gateway
    path("", include("modules.catalog.presentation.api.urls")),
]
