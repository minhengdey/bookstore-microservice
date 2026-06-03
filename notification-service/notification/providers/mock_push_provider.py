import logging
from .base import BaseNotificationProvider

logger = logging.getLogger(__name__)

class MockPushProvider(BaseNotificationProvider):
    def send(self, recipient: str, subject: str, body: str) -> dict:
        logger.info(f"--- MOCK PUSH TO TOKEN {recipient} ---")
        logger.info(f"Title: {subject}")
        logger.info(f"Message: {body}")
        logger.info("--------------------------------------")
        
        return {
            'status': 'SENT',
            'error_message': None
        }
