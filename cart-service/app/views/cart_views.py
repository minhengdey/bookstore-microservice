from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.services import CartService
from app.serializers import CartSerializer, CartItemSerializer
from app.permissions import require_auth, require_customer

_svc = CartService()


class CartView(APIView):
    """POST /carts/ → create cart (internal, no auth check)
       GET  /carts/<customer_id>/ → view cart (requires auth)
    """

    def post(self, request):
        """Internal: called by customer-service when a customer registers."""
        customer_id = request.data.get("customer_id")
        if not customer_id:
            return Response({"error": "customer_id required"}, status=status.HTTP_400_BAD_REQUEST)
        cart = _svc.create_cart(int(customer_id))
        return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)

    @require_auth
    def get(self, request, customer_id):
        ctx = getattr(request, "user_ctx", {})
        if ctx.get("role") == "customer":
            try:
                eid = int(ctx.get("entity_id") or 0)
                if eid != int(customer_id):
                    return Response({"error": "Chỉ được xem giỏ hàng của chính mình."}, status=status.HTTP_403_FORBIDDEN)
            except (TypeError, ValueError):
                return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
        try:
            cart = _svc.get_cart(customer_id)
            return Response(CartSerializer(cart).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    @require_auth
    def delete(self, request, customer_id):
        ctx = getattr(request, "user_ctx", {})
        if ctx.get("role") == "customer":
            try:
                eid = int(ctx.get("entity_id") or 0)
                if eid != int(customer_id):
                    return Response({"error": "Chỉ được xóa giỏ hàng của chính mình."}, status=status.HTTP_403_FORBIDDEN)
            except (TypeError, ValueError):
                return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
        try:
            _svc.clear_cart(customer_id)
            return Response({"message": "Cart cleared"})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


class CartItemView(APIView):
    @require_customer
    def post(self, request, customer_id):
        ctx = getattr(request, "user_ctx", {})
        try:
            eid = int(ctx.get("entity_id") or 0)
            if eid != int(customer_id):
                return Response({"error": "Chỉ được thêm vào giỏ hàng của chính mình."}, status=status.HTTP_403_FORBIDDEN)
        except (TypeError, ValueError):
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
        book_id  = request.data.get("book_id")
        quantity = int(request.data.get("quantity", 1))
        if not book_id:
            return Response({"error": "book_id required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            item = _svc.add_item(customer_id, int(book_id), quantity)
            return Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CartItemDetailView(APIView):
    @require_customer
    def put(self, request, customer_id, item_id):
        ctx = getattr(request, "user_ctx", {})
        try:
            eid = int(ctx.get("entity_id") or 0)
            if eid != int(customer_id):
                return Response({"error": "Chỉ được sửa giỏ hàng của chính mình."}, status=status.HTTP_403_FORBIDDEN)
        except (TypeError, ValueError):
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
        quantity = request.data.get("quantity")
        if quantity is None:
            return Response({"error": "quantity required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            item = _svc.update_item(customer_id, item_id, int(quantity))
            if item is None:
                return Response({"message": "Item removed"})
            return Response(CartItemSerializer(item).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    @require_customer
    def delete(self, request, customer_id, item_id):
        ctx = getattr(request, "user_ctx", {})
        try:
            eid = int(ctx.get("entity_id") or 0)
            if eid != int(customer_id):
                return Response({"error": "Chỉ được xóa item trong giỏ của chính mình."}, status=status.HTTP_403_FORBIDDEN)
        except (TypeError, ValueError):
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
        try:
            _svc.remove_item(customer_id, item_id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
