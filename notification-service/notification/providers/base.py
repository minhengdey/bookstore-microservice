from abc import ABC, abstractmethod

class BaseNotificationProvider(ABC):
    @abstractmethod
    def send(self, recipient: str, subject: str, body: str) -> dict:
        """
        Returns dict:
        {
            'status': 'SENT' | 'FAILED',
            'error_message': str | None
        }
        """
        pass
