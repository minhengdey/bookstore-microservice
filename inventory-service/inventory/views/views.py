from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, AllowAny
from inventory.models import Inventory
from inventory.serializers import (
    InventorySerializer, ReserveStockRequestSerializer, 
    AdjustStockRequestSerializer, PurchaseStockRequestSerializer
)
from inventory.services.inventory_service import InventoryService, OutOfStockError, ConcurrentUpdateError

class IsInventoryAdmin(BasePermission):
    def has_permission(self, request, view):
        role = request.headers.get('X-User-Role')
        return role == 'ADMIN'

class IsInternalService(BasePermission):
    def has_permission(self, request, view):
        return request.headers.get('X-Internal-Service') == 'true'

class InventoryViewSet(viewsets.GenericViewSet):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer

    def get_permissions(self):
        if self.action in ['adjust', 'purchase']:
            return [IsInventoryAdmin()]
        elif self.action in ['reserve', 'confirm', 'release']:
            return [IsInternalService()]
        return [AllowAny()]

    def retrieve(self, request, pk=None):
        try:
            inventory = Inventory.objects.get(pk=pk)
            return Response(InventorySerializer(inventory).data)
        except Inventory.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def adjust(self, request):
        serializer = AdjustStockRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            InventoryService.adjust_stock(
                variant_id=serializer.validated_data['variant_id'],
                quantity=serializer.validated_data['quantity'],
                user_id=serializer.validated_data.get('user_id')
            )
            return Response({"status": "Adjusted successfully"})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def purchase(self, request):
        serializer = PurchaseStockRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            InventoryService.purchase_stock(
                variant_id=serializer.validated_data['variant_id'],
                quantity=serializer.validated_data['quantity'],
                user_id=serializer.validated_data.get('user_id')
            )
            return Response({"status": "Purchased successfully"})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def reserve(self, request):
        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            return Response({"error": "Idempotency-Key header is required"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReserveStockRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            InventoryService.reserve_stock(
                order_id=serializer.validated_data['order_id'],
                correlation_id=serializer.validated_data.get('correlation_id'),
                items=serializer.validated_data['items'],
                idempotency_key=idempotency_key
            )
            return Response({"status": "Reserved successfully"})
        except OutOfStockError as e:
            return Response({"error": str(e), "code": "OUT_OF_STOCK"}, status=status.HTTP_400_BAD_REQUEST)
        except ConcurrentUpdateError as e:
            return Response({"error": str(e), "code": "CONCURRENT_UPDATE"}, status=status.HTTP_409_CONFLICT)

    @action(detail=False, methods=['post'])
    def confirm(self, request):
        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            return Response({"error": "Idempotency-Key header is required"}, status=status.HTTP_400_BAD_REQUEST)

        order_id = request.data.get('order_id')
        if not order_id:
            return Response({"error": "order_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        InventoryService.confirm_reservation(order_id=order_id, idempotency_key=idempotency_key)
        return Response({"status": "Confirmed successfully"})

    @action(detail=False, methods=['post'])
    def release(self, request):
        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            return Response({"error": "Idempotency-Key header is required"}, status=status.HTTP_400_BAD_REQUEST)

        order_id = request.data.get('order_id')
        if not order_id:
            return Response({"error": "order_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        InventoryService.release_reservation(order_id=order_id, idempotency_key=idempotency_key)
        return Response({"status": "Released successfully"})
