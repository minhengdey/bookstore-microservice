import os
from .mock_email_provider import MockEmailProvider
from .mock_sms_provider import MockSMSProvider
from .mock_push_provider import MockPushProvider

class ProviderFactory:
    @staticmethod
    def get_provider(channel: str):
        channel = channel.upper()
        
        # Here we would normally check env vars like EMAIL_PROVIDER=SENDGRID
        # but for now, we route to mocks.
        if channel == 'EMAIL':
            return MockEmailProvider()
        elif channel == 'SMS':
            return MockSMSProvider()
        elif channel == 'PUSH':
            return MockPushProvider()
            
        raise ValueError(f"No provider configured for channel: {channel}")
