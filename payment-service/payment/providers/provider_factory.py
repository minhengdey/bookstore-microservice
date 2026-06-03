import os
from .mock_provider import MockProvider

class ProviderFactory:
    @staticmethod
    def get_provider(provider_name: str = None):
        if not provider_name:
            provider_name = os.environ.get('PAYMENT_PROVIDER', 'MOCK')
            
        provider_name = provider_name.upper()
        
        if provider_name == 'MOCK':
            return MockProvider()
        # Add StripeProvider, VNPayProvider here as they are implemented
        
        raise ValueError(f"Unknown payment provider: {provider_name}")
