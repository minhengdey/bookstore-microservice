import uuid
from .base import BasePaymentProvider

class MockProvider(BasePaymentProvider):
    def create_intent(self, order_id: str, amount: float, currency: str) -> dict:
        return {
            'provider_intent_id': f"mock_pi_{uuid.uuid4().hex[:10]}",
            'client_secret': f"mock_secret_{uuid.uuid4().hex}"
        }

    def process_webhook(self, payload: dict, signature: str) -> dict:
        # Mock validation always passes for testing
        event_id = payload.get('id', f"mock_evt_{uuid.uuid4().hex}")
        event_type = payload.get('type', 'payment_intent.succeeded')
        
        status = 'SUCCEEDED' if event_type == 'payment_intent.succeeded' else 'FAILED'
        txn_type = 'REFUND' if 'refund' in event_type else 'CHARGE'
        
        return {
            'provider_event_id': event_id,
            'transaction_type': txn_type,
            'status': status,
            'amount': payload.get('amount', 0.0),
            'gateway_status': event_type,
            'provider_fee': payload.get('fee', 0.0)
        }

    def refund_payment(self, provider_intent_id: str, amount: float) -> dict:
        return {
            'provider_event_id': f"mock_ref_{uuid.uuid4().hex}",
            'transaction_type': 'REFUND',
            'status': 'SUCCEEDED',
            'amount': amount,
            'gateway_status': 'refund.succeeded',
            'provider_fee': 0.0
        }

    def sync_status(self, provider_intent_id: str) -> dict:
        return {
            'status': 'SUCCEEDED',
            'gateway_status': 'payment_intent.succeeded'
        }
