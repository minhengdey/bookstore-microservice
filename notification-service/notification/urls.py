from django.urls import path, include
from rest_framework.routers import DefaultRouter
from notification.views.views import NotificationTemplateViewSet, NotificationLogViewSet

router = DefaultRouter()
router.register(r'templates', NotificationTemplateViewSet, basename='template')
router.register(r'logs', NotificationLogViewSet, basename='log')

urlpatterns = [
    path('', include(router.urls)),
]
