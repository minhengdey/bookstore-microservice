from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.services import OrderService, DiscountService
from app.serializers import OrderSerializer, DiscountSerializer
from app.permissions import require_auth, require_customer, require_staff, require_manager

_order_svc    = OrderService()
_discount_svc = DiscountService()


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


class OrderListCreateView(APIView):
    @require_auth
    def get(self, request):
        ctx = request.user_ctx
        # Khách hàng chỉ được xem đơn của mình; bỏ qua customer_id từ query.
        if ctx["role"] == "customer":
            try:
                customer_id = int(ctx.get("entity_id") or 0)
            except (TypeError, ValueError):
                customer_id = None
            if not customer_id:
                return Response(OrderSerializer([], many=True).data)
        else:
            customer_id = request.query_params.get("customer_id")
            try:
                customer_id = int(customer_id) if customer_id else None
            except (TypeError, ValueError):
                customer_id = None
        orders = _order_svc.list_orders(customer_id)
        return Response(_paginate_and_search(request, orders, OrderSerializer))

    @require_customer
    def post(self, request):
        try:
            order = _order_svc.create_order(dict(request.data))
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OrderDetailView(APIView):
    @require_auth
    def get(self, request, pk):
        try:
            return Response(OrderSerializer(_order_svc.get_order(pk)).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    @require_staff
    def put(self, request, pk):
        new_status = request.data.get("status")
        try:
            return Response(OrderSerializer(_order_svc.update_status(pk, new_status)).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @require_customer
    def delete(self, request, pk):
        try:
            _order_svc.cancel_order(pk)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DiscountListCreateView(APIView):
    @require_auth
    def get(self, request):
        return Response(_paginate_and_search(request, _discount_svc.list(), DiscountSerializer))

    @require_manager
    def post(self, request):
        try:
            return Response(
                DiscountSerializer(_discount_svc.create(dict(request.data))).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
