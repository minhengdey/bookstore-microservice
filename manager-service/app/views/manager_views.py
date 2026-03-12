from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.services import WarehouseService, InventoryService, SupplierService, PurchaseOrderService
from app.serializers import (
    WarehouseSerializer, InventorySerializer,
    SupplierSerializer, PurchaseOrderSerializer,
)

_warehouse_svc = WarehouseService()
_inventory_svc = InventoryService()
_supplier_svc = SupplierService()
_po_svc = PurchaseOrderService()


class WarehouseListCreateView(APIView):
    def get(self, request):
        return Response(WarehouseSerializer(_warehouse_svc.list(), many=True).data)
    def post(self, request):
        try:
            w = _warehouse_svc.create(dict(request.data))
            return Response(WarehouseSerializer(w).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class WarehouseDetailView(APIView):
    def get(self, request, pk):
        try: return Response(WarehouseSerializer(_warehouse_svc.get(pk)).data)
        except ValueError as e: return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
    def put(self, request, pk):
        try: return Response(WarehouseSerializer(_warehouse_svc.update(pk, dict(request.data))).data)
        except ValueError as e: return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
    def delete(self, request, pk):
        try: _warehouse_svc.delete(pk); return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e: return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


class InventoryListCreateView(APIView):
    def get(self, request):
        return Response(InventorySerializer(_inventory_svc.list(), many=True).data)
    def post(self, request):
        try:
            inv = _inventory_svc.create(dict(request.data))
            return Response(InventorySerializer(inv).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SupplierListCreateView(APIView):
    def get(self, request): return Response(SupplierSerializer(_supplier_svc.list(), many=True).data)
    def post(self, request):
        try: return Response(SupplierSerializer(_supplier_svc.create(dict(request.data))).data, status=status.HTTP_201_CREATED)
        except Exception as e: return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SupplierDetailView(APIView):
    def get(self, request, pk):
        try: return Response(SupplierSerializer(_supplier_svc.get(pk)).data)
        except ValueError as e: return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
    def put(self, request, pk):
        try: return Response(SupplierSerializer(_supplier_svc.update(pk, dict(request.data))).data)
        except ValueError as e: return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
    def delete(self, request, pk):
        try: _supplier_svc.delete(pk); return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e: return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


class PurchaseOrderListCreateView(APIView):
    def get(self, request): return Response(PurchaseOrderSerializer(_po_svc.list(), many=True).data)
    def post(self, request):
        try: return Response(PurchaseOrderSerializer(_po_svc.create(dict(request.data))).data, status=status.HTTP_201_CREATED)
        except ValueError as e: return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PurchaseOrderDetailView(APIView):
    def get(self, request, pk):
        try: return Response(PurchaseOrderSerializer(_po_svc.get(pk)).data)
        except ValueError as e: return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
    def put(self, request, pk):
        new_status = request.data.get("status")
        try: return Response(PurchaseOrderSerializer(_po_svc.update_status(pk, new_status)).data)
        except ValueError as e: return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
