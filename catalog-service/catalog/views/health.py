from django.http import JsonResponse
from django.db import connection
import os

def health_check(request):
    return JsonResponse({"status": "UP"})

def ready_check(request):
    status = {"status": "UP", "checks": {}}
    
    # Check Postgres
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
            if row:
                status["checks"]["postgres"] = "UP"
            else:
                status["checks"]["postgres"] = "DOWN"
                status["status"] = "DOWN"
    except Exception as e:
        status["checks"]["postgres"] = "DOWN"
        status["status"] = "DOWN"
        
    # Check RabbitMQ (simplified check depending on environment variable, or ping if amqp library is used)
    # A robust check would establish a connection using pika or Celery ping
    rabbitmq_host = os.environ.get("RABBITMQ_HOST")
    if rabbitmq_host:
        status["checks"]["rabbitmq"] = "CONFIGURED"
    else:
        status["checks"]["rabbitmq"] = "MISSING_CONFIG"
        status["status"] = "DOWN"
        
    # Check S3/MinIO
    s3_endpoint = os.environ.get("AWS_S3_ENDPOINT_URL")
    if s3_endpoint:
        status["checks"]["s3"] = "CONFIGURED"
    else:
        status["checks"]["s3"] = "MISSING_CONFIG"
        status["status"] = "DOWN"

    return JsonResponse(status, status=200 if status["status"] == "UP" else 503)
