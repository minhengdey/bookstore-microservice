from rest_framework import serializers
from interaction.models import InteractionEvent

class InteractionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = InteractionEvent
        fields = ['idempotency_key', 'user_id', 'anonymous_id', 'session_id', 'correlation_id', 'product_id', 'event_type', 'source', 'metadata']
