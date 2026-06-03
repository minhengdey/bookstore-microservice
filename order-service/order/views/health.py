from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connection
from order.services.cart_service import CartService
import os

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({"status": "ok", "service": "order-service"})

@api_view(['GET'])
@permission_classes([AllowAny])
def ready_check(request):
    try:
        connection.ensure_connection()
        db_ok = True
    except Exception:
        db_ok = False
        
    try:
        CartService().redis_client.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    if db_ok and redis_ok:
        return Response({"status": "ready", "database": "connected", "redis": "connected"})
    return Response({"status": "not ready", "database": db_ok, "redis": redis_ok}, status=503)
