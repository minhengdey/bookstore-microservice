from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.services import ShippingService
from app.serializers import ShippingSerializer, ShippingMethodSerializer

_svc = ShippingService()


class ShippingMethodListView(APIView):
    def get(self, request): return Response(ShippingMethodSerializer(_svc.list_methods(), many=True).data)


class ShippingListCreateView(APIView):
    def get(self, request): return Response(ShippingSerializer(_svc.list(), many=True).data)

    def post(self, request):
        """POST body: {order_id, shipping_method_id, address: {...}}"""
        try:
            shipping = _svc.create_shipment(
                order_id=int(request.data["order_id"]),
                method_id=int(request.data["shipping_method_id"]),
                address_data=request.data.get("address", {}),
            )
            return Response(ShippingSerializer(shipping).data, status=status.HTTP_201_CREATED)
        except (KeyError, ValueError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ShippingDetailView(APIView):
    def get(self, request, pk):
        try: return Response(ShippingSerializer(_svc.get(pk)).data)
        except ValueError as e: return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        try: return Response(ShippingSerializer(_svc.update_status(pk, request.data.get("status"))).data)
        except ValueError as e: return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
