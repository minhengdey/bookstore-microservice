from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, BasePermission
from order.models import Order
from order.serializers import OrderSerializer, CheckoutRequestSerializer, CartItemSerializer
from order.services.cart_service import CartService
from order.services.saga_manager import OrderSagaManager
from order.services.auth import verify_service_signature

class InternalServicePermission(BasePermission):
    def has_permission(self, request, view):
        service_name = request.headers.get('X-Service-Name')
        timestamp = request.headers.get('X-Timestamp')
        signature = request.headers.get('X-Service-Signature')
        
        if not all([service_name, timestamp, signature]):
            return False
            
        return verify_service_signature(service_name, timestamp, signature)

class OrderViewSet(viewsets.GenericViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [AllowAny] # In reality, use IsAuthenticated for user endpoints

    def retrieve(self, request, pk=None):
        try:
            # Optimize with select_related/prefetch_related
            order = Order.objects.select_related('saga').prefetch_related('items', 'history').get(pk=pk)
            return Response(OrderSerializer(order).data)
        except Order.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def checkout(self, request):
        serializer = CheckoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_id = serializer.validated_data['user_id']
        shipping_address = serializer.validated_data['shipping_address']
        
        cart_service = CartService()
        cart_items = cart_service.get_cart(user_id=str(user_id))
        
        if not cart_items:
            return Response({"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            order = OrderSagaManager.start_checkout(
                user_id=str(user_id),
                cart_items=cart_items,
                shipping_address=shipping_address
            )
            return Response({"order_id": order.id, "status": order.status}, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # Cart endpoints
    @action(detail=False, methods=['get'])
    def cart(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({"error": "user_id required"}, status=status.HTTP_400_BAD_REQUEST)
            
        items = CartService().get_cart(user_id=user_id)
        return Response(items)

    @action(detail=False, methods=['post'], url_path='cart/add')
    def add_to_cart(self, request):
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({"error": "user_id required"}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer = CartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            result = CartService().add_item(
                user_id=user_id,
                variant_id=str(serializer.validated_data['variant_id']),
                quantity=serializer.validated_data['quantity']
            )
            return Response(result)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='cart/remove')
    def remove_from_cart(self, request):
        user_id = request.data.get('user_id')
        variant_id = request.data.get('variant_id')
        if not user_id or not variant_id:
            return Response({"error": "user_id and variant_id required"}, status=status.HTTP_400_BAD_REQUEST)
            
        CartService().remove_item(user_id=user_id, variant_id=variant_id)
        return Response({"status": "removed"})
