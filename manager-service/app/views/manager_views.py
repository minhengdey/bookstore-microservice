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


def _parse_positive_int(value, default):
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


def _paginate_and_search(request, objs, serializer_cls):
    if hasattr(objs, "order_by"):
        objs = objs.order_by("id")
    else:
        objs = sorted(objs, key=lambda x: getattr(x, "id", 0))
    data = list(serializer_cls(objs, many=True).data)
    keyword = (request.query_params.get("search") or "").strip().lower()
    if keyword:
        data = [
            item for item in data
            if any(keyword in str(value).lower() for value in item.values() if value is not None)
        ]
    page = _parse_positive_int(request.query_params.get("page"), 1)
    page_size = min(_parse_positive_int(request.query_params.get("page_size"), 10), 200)
    total = len(data)
    total_pages = max(1, (total + page_size - 1) // page_size)
    if page > total_pages:
        page = total_pages
    start = (page - 1) * page_size
    end = start + page_size
    next_page = page + 1 if page < total_pages else None
    prev_page = page - 1 if page > 1 else None
    return {
        "count": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "next_page": next_page,
        "prev_page": prev_page,
        "results": data[start:end],
    }


class WarehouseListCreateView(APIView):
    def get(self, request):
        return Response(_paginate_and_search(request, _warehouse_svc.list(), WarehouseSerializer))
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
        return Response(_paginate_and_search(request, _inventory_svc.list(), InventorySerializer))
    def post(self, request):
        try:
            inv = _inventory_svc.create(dict(request.data))
            return Response(InventorySerializer(inv).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SupplierListCreateView(APIView):
    def get(self, request): return Response(_paginate_and_search(request, _supplier_svc.list(), SupplierSerializer))
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
    def get(self, request): return Response(_paginate_and_search(request, _po_svc.list(), PurchaseOrderSerializer))
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
