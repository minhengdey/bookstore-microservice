import uuid
from django.db import transaction
from django.utils import timezone
from interaction.models import InteractionEvent, OutboxEvent

EVENT_WEIGHTS = {
    'VIEW': 1.0,
    'CLICK': 2.0,
    'SEARCH': 3.0,
    'ADD_TO_CART': 5.0,
    'REMOVE_FROM_CART': -2.0,
    'WISHLIST': 4.0,
    'PURCHASE': 10.0,
    'RATING': 6.0,
    'REVIEW': 7.0
}

class InteractionService:
    @staticmethod
    @transaction.atomic
    def record_interaction(user_id: str = None, anonymous_id: str = None, session_id: str = None, 
                           correlation_id: str = None, product_id: str = None, event_type: str = None, 
                           source: str = 'WEB', metadata: dict = None, idempotency_key: str = None) -> dict:
        
        if idempotency_key:
            existing = InteractionEvent.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                return {'id': str(existing.id), 'status': 'already_recorded'}

        weight = EVENT_WEIGHTS.get(event_type.upper(), 1.0)
        metadata = metadata or {}
        
        event = InteractionEvent.objects.create(
            user_id=user_id,
            anonymous_id=anonymous_id,
            session_id=session_id,
            correlation_id=correlation_id or session_id,
            product_id=product_id,
            event_type=event_type.upper(),
            weight=weight,
            source=source,
            metadata=metadata,
            idempotency_key=idempotency_key
        )
        
        # Publish to Outbox
        OutboxEvent.objects.create(
            aggregate_id=event.id,
            aggregate_type='InteractionEvent',
            event_type=f'interaction.{event.event_type.lower()}',
            message_id=uuid.uuid4(),
            payload={
                "event_id": str(uuid.uuid4()),
                "event_type": f'interaction.{event.event_type.lower()}',
                "event_version": "v1",
                "correlation_id": str(event.correlation_id),
                "causation_id": str(event.id),
                "occurred_at": timezone.now().isoformat(),
                "user_id": str(event.user_id) if event.user_id else None,
                "anonymous_id": str(event.anonymous_id) if event.anonymous_id else None,
                "session_id": str(event.session_id),
                "product_id": str(event.product_id),
                "weight": weight,
                "source": source,
                "metadata": metadata
            }
        )
        
        return {
            'id': str(event.id),
            'status': 'recorded'
        }
