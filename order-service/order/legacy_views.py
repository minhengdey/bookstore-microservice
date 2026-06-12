from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Sum
from .legacy_services import OrderService, DiscountService
from .legacy_serializers import OrderSerializer, DiscountSerializer
from common.auth import require_auth, require_customer, require_staff, require_manager, require_internal
from .legacy_models import LegacyOrder as Order, OrderStatus

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
            data = dict(request.data)
            ctx = request.user_ctx
            try:
                customer_id = int(ctx.get("entity_id") or 0)
            except (TypeError, ValueError):
                return Response({"error": "Invalid customer context"}, status=status.HTTP_400_BAD_REQUEST)
            data["customer_id"] = customer_id
            order = _order_svc.create_order(data)
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


_PURCHASE_ORDER_STATUSES = (
    OrderStatus.PENDING_PAYMENT,
    OrderStatus.PAID,
    OrderStatus.PROCESSING,
    OrderStatus.SHIPPING,
    OrderStatus.DELIVERED,
)


class InternalRecommenderOrdersView(APIView):
    """Orders + purchase aggregates for recommender-ai-service (internal auth)."""

    @require_internal
    def get(self, request):
        customer_id = request.query_params.get("customer_id")
        qs = Order.objects.filter(status__in=_PURCHASE_ORDER_STATUSES).prefetch_related("items")
        if customer_id:
            try:
                qs = qs.filter(customer_id=int(customer_id))
            except (TypeError, ValueError):
                return Response({"error": "Invalid customer_id"}, status=status.HTTP_400_BAD_REQUEST)

        orders = []
        by_customer: dict[int, set[int]] = {}
        for order in qs:
            product_ids = [int(item.product_id) for item in order.items.all()]
            orders.append({
                "customer_id": int(order.customer_id),
                "items": [{"product_id": pid} for pid in product_ids],
            })
            bucket = by_customer.setdefault(int(order.customer_id), set())
            bucket.update(product_ids)

        purchase_signals = [
            {"customer_id": cid, "purchase_ids": sorted(pids)}
            for cid, pids in sorted(by_customer.items())
        ]
        return Response({
            "orders": orders,
            "purchase_signals": purchase_signals,
        })


class OrderMetricsView(APIView):
    @require_internal
    def get(self, request):
        total_orders = Order.objects.count()
        total_revenue = Order.objects.filter(status="DELIVERED").aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        status_counts = Order.objects.values('status').annotate(count=Count('id'))
        status_data = {item['status']: item['count'] for item in status_counts}

        data = {
            "total_orders": total_orders,
            "total_revenue": float(total_revenue),
            "status_breakdown": status_data,
        }
        return Response(data, status=status.HTTP_200_OK)

class InternalBulkOrderStatusView(APIView):
    @require_internal
    def post(self, request):
        try:
            order_ids = request.data.get("order_ids", [])
            from .legacy_models import LegacyOrder as Order
            orders = Order.objects.filter(id__in=order_ids)
            statuses = {o.id: o.status for o in orders}
            return Response({"statuses": statuses})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InternalOrderMarkPaidView(APIView):
    @require_internal
    def post(self, request, pk):
        try:
            order = _order_svc.get_order(pk)
            if order.status != OrderStatus.PAID:
                order = _order_svc.update_status(pk, OrderStatus.PAID)
            return Response(OrderSerializer(order).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InternalOrderShippingContextView(APIView):
    @require_internal
    def get(self, request, pk):
        try:
            return Response(_order_svc.get_shipping_context(pk))
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


class InternalOrderAdvanceProcessingView(APIView):
    @require_internal
    def post(self, request, pk):
        try:
            order = _order_svc.advance_to_processing(pk)
            return Response(OrderSerializer(order).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OrderReturnRequestView(APIView):
    @require_customer
    def post(self, request, pk):
        try:
            ctx = request.user_ctx
            customer_id = int(ctx.get("entity_id") or 0)
            order = _order_svc.request_return(pk, customer_id=customer_id)
            return Response(OrderSerializer(order).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StaffBulkOrderUpdateView(APIView):
    @require_staff
    def post(self, request):
        order_ids = request.data.get("order_ids", [])
        action = request.data.get("action")
        new_status = request.data.get("status")
        if not order_ids:
            return Response({"error": "order_ids is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not action and not new_status:
            return Response({"error": "action or status is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            result = _order_svc.bulk_update_status(order_ids, action=action, new_status=new_status)
            return Response(result)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
