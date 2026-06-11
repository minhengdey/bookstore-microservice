from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from interaction.models import InteractionEvent, Review, Wishlist, Ticket, TicketReply
from interaction.serializers import InteractionEventSerializer, ReviewSerializer, WishlistSerializer, TicketSerializer, TicketReplySerializer
from interaction.services.interaction_service import InteractionService

class WishlistViewSet(viewsets.ModelViewSet):
    queryset = Wishlist.objects.all()
    serializer_class = WishlistSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        qs = super().get_queryset()
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        return qs

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        qs = super().get_queryset()
        product_id = self.request.query_params.get('product_id')
        if product_id:
            qs = qs.filter(product_id=product_id)
        return qs

class InteractionViewSet(viewsets.GenericViewSet):
    serializer_class = InteractionEventSerializer
    permission_classes = [AllowAny] # In production, protect this endpoint (Gateway only)
    
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            result = InteractionService.record_interaction(
                user_id=serializer.validated_data.get('user_id'),
                anonymous_id=serializer.validated_data.get('anonymous_id'),
                session_id=serializer.validated_data.get('session_id'),
                correlation_id=serializer.validated_data.get('correlation_id'),
                product_id=serializer.validated_data.get('product_id'),
                event_type=serializer.validated_data.get('event_type'),
                source=serializer.validated_data.get('source', 'WEB'),
                metadata=serializer.validated_data.get('metadata', {}),
                idempotency_key=serializer.validated_data.get('idempotency_key')
            )
            return Response(result, status=status.HTTP_201_CREATED if result.get('status') == 'recorded' else status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all().prefetch_related('replies')
    serializer_class = TicketSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        qs = super().get_queryset()
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        return qs

class TicketReplyViewSet(viewsets.ModelViewSet):
    queryset = TicketReply.objects.all()
    serializer_class = TicketReplySerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        qs = super().get_queryset()
        ticket_id = self.request.query_params.get('ticket_id')
        if ticket_id:
            qs = qs.filter(ticket_id=ticket_id)
        return qs
