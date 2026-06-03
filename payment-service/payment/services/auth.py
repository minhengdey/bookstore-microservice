import os
import hmac
import hashlib
import time

def verify_service_signature(service_name, timestamp, signature):
    secret = os.environ.get('INTERNAL_SERVICE_SECRET', 'ecommerce_shared_secret')
    
    try:
        ts = int(timestamp)
        if abs(time.time() - ts) > 300:
            return False
    except (ValueError, TypeError):
        return False
        
    message = f"{service_name}:{timestamp}".encode('utf-8')
    expected_signature = hmac.new(secret.encode('utf-8'), message, hashlib.sha256).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)
