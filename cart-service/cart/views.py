from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from common.auth import require_auth, require_customer, require_internal
from .services import CartService
from .serializers import CartSerializer

_cart_svc = CartService()


def _customer_id_from_request(request):
    ctx = getattr(request, "user_ctx", {})
    return int(ctx.get("entity_id") or ctx.get("user_id") or request.user_id)


def _can_access_cart(request, customer_id):
    ctx = getattr(request, "user_ctx", {})
    role = ctx.get("role")
    entity_id = ctx.get("entity_id") or ctx.get("user_id")
    return role in ("staff", "manager", "admin") or str(entity_id) == str(customer_id)


def _forbidden_response():
    return Response({"error": "Forbidden: cannot access this cart"}, status=status.HTTP_403_FORBIDDEN)


def _product_id_from_payload(data):
    return int(data.get("product_id") or data["product_id"])


def _serialize_cart(cart, response_status=status.HTTP_200_OK):
    return Response(CartSerializer(cart).data, status=response_status)

class CartView(APIView):
    @require_customer
    def get(self, request):
        cart = _cart_svc.get_cart(_customer_id_from_request(request))
        return _serialize_cart(cart)
        
    @require_customer
    def post(self, request):
        # Legacy POST /cart/ - keeping for backwards compatibility, but recommend POST /cart/add
        try:
            product_id = _product_id_from_payload(request.data)
            quantity = int(request.data.get("quantity", 1))
            unit_price = float(request.data.get("unit_price", 0))
            cart = _cart_svc.add_item(_customer_id_from_request(request), product_id, quantity, unit_price)
            return _serialize_cart(cart, status.HTTP_201_CREATED)
        except (KeyError, ValueError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CartAddView(APIView):
    @require_customer
    def post(self, request):
        try:
            product_id = _product_id_from_payload(request.data)
            quantity = int(request.data.get("quantity", 1))
            unit_price = float(request.data.get("unit_price", 0))
            cart = _cart_svc.add_item(_customer_id_from_request(request), product_id, quantity, unit_price)
            return _serialize_cart(cart, status.HTTP_201_CREATED)
        except (KeyError, ValueError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CartDetailView(APIView):
    @require_auth
    def get(self, request, customer_id):
        if not _can_access_cart(request, customer_id):
            return _forbidden_response()
        cart = _cart_svc.get_cart(customer_id)
        return _serialize_cart(cart)

    @require_auth
    def delete(self, request, customer_id):
        if not _can_access_cart(request, customer_id):
            return _forbidden_response()
        cart = _cart_svc.clear_cart(customer_id)
        return _serialize_cart(cart)


class CartItemsView(APIView):
    @require_auth
    def get(self, request, customer_id):
        if not _can_access_cart(request, customer_id):
            return _forbidden_response()
        cart = _cart_svc.get_cart(customer_id)
        return Response(CartSerializer(cart).data.get("items", []))

    @require_auth
    def post(self, request, customer_id):
        if not _can_access_cart(request, customer_id):
            return _forbidden_response()
        try:
            product_id = _product_id_from_payload(request.data)
            quantity = int(request.data.get("quantity", 1))
            unit_price = float(request.data.get("unit_price", 0))
            cart = _cart_svc.add_item(customer_id, product_id, quantity, unit_price)
            return _serialize_cart(cart, status.HTTP_201_CREATED)
        except (KeyError, ValueError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CartItemView(APIView):
    @require_customer
    def patch(self, request, item_id):
        try:
            quantity = int(request.data.get("quantity", 1))
            cart = _cart_svc.update_item(_customer_id_from_request(request), item_id, quantity)
            return _serialize_cart(cart)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
    @require_customer
    def delete(self, request, item_id):
        try:
            cart = _cart_svc.remove_item(_customer_id_from_request(request), item_id)
            return _serialize_cart(cart)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CustomerCartItemView(APIView):
    @require_auth
    def put(self, request, customer_id, item_id):
        return self.patch(request, customer_id, item_id)

    @require_auth
    def patch(self, request, customer_id, item_id):
        if not _can_access_cart(request, customer_id):
            return _forbidden_response()
        try:
            quantity = int(request.data.get("quantity", 1))
            cart = _cart_svc.update_item(customer_id, item_id, quantity)
            return _serialize_cart(cart)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @require_auth
    def delete(self, request, customer_id, item_id):
        if not _can_access_cart(request, customer_id):
            return _forbidden_response()
        cart = _cart_svc.remove_item(customer_id, item_id)
        return _serialize_cart(cart)


class InternalCartView(APIView):
    @require_internal
    def get(self, request, customer_id):
        cart = _cart_svc.get_cart(customer_id)
        return _serialize_cart(cart)
        
    @require_internal
    def delete(self, request, customer_id):
        cart = _cart_svc.clear_cart(customer_id)
        return _serialize_cart(cart)
