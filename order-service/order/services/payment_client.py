import os
import requests
import logging
from order.services.auth import generate_service_signature

logger = logging.getLogger(__name__)

class PaymentClient:
    @staticmethod
    def create_payment_session(order_id: str, amount: float):
        payment_url = os.environ.get('PAYMENT_SERVICE_URL', 'http://payment-service:8000')
        url = f"{payment_url}/api/v1/payments/create"
        
        headers = generate_service_signature()
        payload = {
            "order_id": str(order_id),
            "amount": float(amount)
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error(f"Payment API error: {response.status_code} - {response.text}")
                raise Exception(f"Payment service error: {response.text}")
        except requests.RequestException as e:
            logger.error(f"Payment API connection error: {e}")
            raise Exception("Payment service unavailable")
