from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from notification.models import NotificationTemplate, NotificationLog
from notification.serializers import NotificationTemplateSerializer, NotificationLogSerializer

class NotificationTemplateViewSet(viewsets.ModelViewSet):
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [AllowAny] # In reality, IsAdminUser

class NotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NotificationLog.objects.all().order_by('-created_at')
    serializer_class = NotificationLogSerializer
    permission_classes = [AllowAny] # In reality, IsAdminUser
