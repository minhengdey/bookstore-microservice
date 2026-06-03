from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connection
import os

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({"status": "ok", "service": "payment-service"})

@api_view(['GET'])
@permission_classes([AllowAny])
def ready_check(request):
    try:
        connection.ensure_connection()
        db_ok = True
    except Exception:
        db_ok = False
        
    if db_ok:
        return Response({"status": "ready", "database": "connected"})
    return Response({"status": "not ready", "database": db_ok}, status=503)
