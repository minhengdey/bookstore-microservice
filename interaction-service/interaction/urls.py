from django.urls import path, include
from rest_framework.routers import DefaultRouter
from interaction.views.views import InteractionViewSet

router = DefaultRouter()
router.register(r'', InteractionViewSet, basename='interaction')

urlpatterns = [
    path('', include(router.urls)),
]
