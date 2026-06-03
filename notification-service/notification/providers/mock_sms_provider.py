import logging
from .base import BaseNotificationProvider

logger = logging.getLogger(__name__)

class MockSMSProvider(BaseNotificationProvider):
    def send(self, recipient: str, subject: str, body: str) -> dict:
        logger.info(f"--- MOCK SMS TO {recipient} ---")
        logger.info(f"Message: {body}")
        logger.info("-------------------------------")
        
        return {
            'status': 'SENT',
            'error_message': None
        }
