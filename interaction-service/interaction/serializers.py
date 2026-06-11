from rest_framework import serializers
from interaction.models import InteractionEvent, Review, Wishlist, Ticket, TicketReply

class InteractionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = InteractionEvent
        fields = ['idempotency_key', 'user_id', 'anonymous_id', 'session_id', 'correlation_id', 'product_id', 'event_type', 'source', 'metadata']

class TicketReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketReply
        fields = '__all__'

class TicketSerializer(serializers.ModelSerializer):
    replies = TicketReplySerializer(many=True, read_only=True)
    
    class Meta:
        model = Ticket
        fields = '__all__'

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = '__all__'

class WishlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wishlist
        fields = '__all__'
