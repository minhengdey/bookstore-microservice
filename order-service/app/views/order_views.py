from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.services import OrderService, DiscountService
from app.serializers import OrderSerializer, DiscountSerializer
from app.permissions import require_auth, require_customer, require_staff, require_manager

_order_svc    = OrderService()
_discount_svc = DiscountService()


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
        return Response(OrderSerializer(orders, many=True).data)

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
        return Response(DiscountSerializer(_discount_svc.list(), many=True).data)

    @require_manager
    def post(self, request):
        try:
            return Response(
                DiscountSerializer(_discount_svc.create(dict(request.data))).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
