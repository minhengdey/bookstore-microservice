from abc import ABC, abstractmethod

class BasePaymentProvider(ABC):
    @abstractmethod
    def create_intent(self, order_id: str, amount: float, currency: str) -> dict:
        """
        Returns dict containing provider_intent_id and client_secret
        """
        pass

    @abstractmethod
    def process_webhook(self, payload: dict, signature: str) -> dict:
        """
        Returns normalized dict:
        {
            'provider_event_id': str,
            'transaction_type': str, # 'CHARGE' or 'REFUND'
            'status': str, # 'SUCCEEDED', 'FAILED'
            'amount': float,
            'gateway_status': str,
            'provider_fee': float
        }
        """
        pass

    @abstractmethod
    def refund_payment(self, provider_intent_id: str, amount: float) -> dict:
        """
        Returns normalized dict similar to process_webhook output
        """
        pass

    @abstractmethod
    def sync_status(self, provider_intent_id: str) -> dict:
        """
        Queries gateway directly to get current status.
        """
        pass
