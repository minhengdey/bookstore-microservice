from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, BasePermission
from payment.serializers import CreatePaymentSerializer, RefundPaymentSerializer
from payment.services.payment_service import PaymentService
from payment.services.auth import verify_service_signature

class InternalServicePermission(BasePermission):
    def has_permission(self, request, view):
        service_name = request.headers.get('X-Service-Name')
        timestamp = request.headers.get('X-Timestamp')
        signature = request.headers.get('X-Service-Signature')
        
        if not all([service_name, timestamp, signature]):
            return False
            
        return verify_service_signature(service_name, timestamp, signature)

class PaymentViewSet(viewsets.ViewSet):
    
    def get_permissions(self):
        if self.action in ['create_payment', 'refund']:
            return [InternalServicePermission()]
        return [AllowAny()] # Webhook needs to be public

    @action(detail=False, methods=['post'], url_path='create')
    def create_payment(self, request):
        serializer = CreatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            result = PaymentService.create_payment(
                order_id=str(serializer.validated_data['order_id']),
                amount=float(serializer.validated_data['amount']),
                correlation_id=str(serializer.validated_data['correlation_id']),
                idempotency_key=serializer.validated_data.get('idempotency_key')
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='refund')
    def refund(self, request, pk=None):
        serializer = RefundPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            result = PaymentService.refund_payment(
                payment_id=pk,
                reason=serializer.validated_data['reason'],
                idempotency_key=serializer.validated_data.get('idempotency_key')
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='webhook/(?P<provider>[^/.]+)')
    def webhook(self, request, provider=None):
        signature = request.headers.get('Stripe-Signature') or request.headers.get('Webhook-Signature') or 'mock_signature'
        payload = request.data
        
        try:
            PaymentService.process_webhook(provider, payload, signature)
            return Response({"status": "received"}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Important: always return 200 to webhooks even on internal error to prevent spamming, 
            # OR 500 if we explicitly want provider to retry. Here we'll just log and 400.
            return Response({"error": "Webhook processing failed"}, status=status.HTTP_400_BAD_REQUEST)
