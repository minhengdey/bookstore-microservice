import os
import hmac
import hashlib
import time

def generate_service_signature():
    secret = os.environ.get('INTERNAL_SERVICE_SECRET', 'ecommerce_shared_secret')
    timestamp = str(int(time.time()))
    service_name = os.environ.get('SERVICE_NAME', 'order-service')
    
    message = f"{service_name}:{timestamp}".encode('utf-8')
    signature = hmac.new(secret.encode('utf-8'), message, hashlib.sha256).hexdigest()
    
    return {
        'X-Service-Name': service_name,
        'X-Timestamp': timestamp,
        'X-Service-Signature': signature,
        'X-Internal-Service': 'true'
    }

def verify_service_signature(service_name, timestamp, signature):
    secret = os.environ.get('INTERNAL_SERVICE_SECRET', 'ecommerce_shared_secret')
    
    # Check timestamp expiration (e.g., 5 minutes)
    try:
        ts = int(timestamp)
        if abs(time.time() - ts) > 300:
            return False
    except (ValueError, TypeError):
        return False
        
    message = f"{service_name}:{timestamp}".encode('utf-8')
    expected_signature = hmac.new(secret.encode('utf-8'), message, hashlib.sha256).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)
