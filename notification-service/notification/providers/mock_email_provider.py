import logging
from .base import BaseNotificationProvider

logger = logging.getLogger(__name__)

class MockEmailProvider(BaseNotificationProvider):
    def send(self, recipient: str, subject: str, body: str) -> dict:
        logger.info(f"--- MOCK EMAIL TO {recipient} ---")
        logger.info(f"Subject: {subject}")
        logger.info(f"Body: {body}")
        logger.info("---------------------------------")
        
        return {
            'status': 'SENT',
            'error_message': None
        }
