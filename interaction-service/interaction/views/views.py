from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from interaction.models import InteractionEvent
from interaction.serializers import InteractionEventSerializer
from interaction.services.interaction_service import InteractionService

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
