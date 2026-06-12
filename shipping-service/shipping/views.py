import os

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from common.auth import require_auth, require_staff, require_internal
from common.client import InternalClient
from .services import ShippingService, ShippingMethodService, ShippingZoneService
from .models import ShippingState
from .serializers import ShippingSerializer, ShippingMethodSerializer

_ship_svc = ShippingService()
_method_svc = ShippingMethodService()
_zone_svc = ShippingZoneService()
_order_client = InternalClient()
ORDER_SERVICE_URL = os.environ.get("ORDER_SERVICE_URL", "http://order-service:8000")


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


def _fetch_shipping_context(order_id):
    try:
        resp = _order_client.get(f"{ORDER_SERVICE_URL}/orders/internal/{order_id}/shipping-context/")
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def _create_from_request_data(data):
    order_id = int(data["order_id"])
    shipping_method_id = data.get("shipping_method_id")
    address = data.get("address")
    if shipping_method_id is not None:
        shipping_method_id = int(shipping_method_id)
    if not address:
        context = _fetch_shipping_context(order_id)
        if context:
            shipping_method_id = shipping_method_id or context.get("shipping_method_id")
            address = context.get("shipping_address_snapshot")
    return _ship_svc.create_shipping(
        order_id,
        shipping_method_id=shipping_method_id,
        address_data=address,
    )


class ShippingMethodListView(APIView):
    @require_auth
    def get(self, request):
        return Response(_paginate_and_search(request, _method_svc.list(), ShippingMethodSerializer))

    @require_staff
    def post(self, request):
        try:
            return Response(
                ShippingMethodSerializer(_method_svc.create(dict(request.data))).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ShippingZoneLookupView(APIView):
    @require_auth
    def get(self, request):
        city = request.query_params.get("city", "")
        distance_km = _zone_svc.lookup_distance(city)
        return Response({"city": city, "distance_km": distance_km})


class ShippingListView(APIView):
    @require_staff
    def get(self, request):
        return Response(_paginate_and_search(request, _ship_svc.list(), ShippingSerializer))


class ShippingDetailView(APIView):
    @require_auth
    def get(self, request, pk):
        try:
            return Response(ShippingSerializer(_ship_svc.get(pk)).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    @require_staff
    def put(self, request, pk):
        new_status = request.data.get("status")
        description = request.data.get("description", "")
        try:
            shipping = _ship_svc.update_shipping_status(pk, new_status, description)
            return Response(ShippingSerializer(shipping).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InternalShippingCreateView(APIView):
    @require_internal
    def post(self, request):
        try:
            shipping = _create_from_request_data(request.data)
            return Response(ShippingSerializer(shipping).data, status=status.HTTP_201_CREATED)
        except (KeyError, ValueError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ShippingCreateView(APIView):
    @require_auth
    def post(self, request):
        try:
            shipping = _create_from_request_data(request.data)
            return Response(ShippingSerializer(shipping).data, status=status.HTTP_201_CREATED)
        except (KeyError, ValueError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ShippingByOrderView(APIView):
    @require_auth
    def get(self, request, order_id):
        shipping = _ship_svc.get_by_order_id(order_id)
        if not shipping:
            return Response({"error": "Shipping not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(ShippingSerializer(shipping).data)


class InternalShippingStatusView(APIView):
    @require_internal
    def post(self, request):
        order_id = request.data.get("order_id")
        new_status = request.data.get("status", "processing")
        if not order_id:
            return Response({"error": "order_id required"}, status=status.HTTP_400_BAD_REQUEST)

        shipping = _ship_svc.get_by_order_id(int(order_id))
        if not shipping:
            context = _fetch_shipping_context(int(order_id))
            shipping_method_id = context.get("shipping_method_id") if context else None
            address = context.get("shipping_address_snapshot") if context else None
            shipping = _ship_svc.create_shipping(
                int(order_id),
                shipping_method_id=shipping_method_id,
                address_data=address,
            )

        shipping = _ship_svc.sync_from_order_status(shipping.id, new_status)
        return Response(ShippingSerializer(shipping).data)


class ShippingFeeCalculatorView(APIView):
    @require_auth
    def post(self, request):
        try:
            method_id = int(request.data.get("shipping_method_id"))
            total_weight = float(request.data.get("total_weight", 1.0))
            distance_km = float(request.data.get("distance_km", 10.0))
            return Response(_method_svc.calculate_fee(method_id, total_weight, distance_km))
        except (TypeError, ValueError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
