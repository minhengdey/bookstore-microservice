from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.services import CustomerService
from app.serializers import WebAddressSerializer

_svc = CustomerService()


class AddressListCreateView(APIView):
    def get(self, request, customer_id):
        try:
            addresses = _svc.list_addresses(customer_id)
            return Response(WebAddressSerializer(addresses, many=True).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, customer_id):
        ser = WebAddressSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            data = {k: v for k, v in ser.validated_data.items() if k != "customer"}
            address = _svc.add_address(customer_id, data)
            return Response(WebAddressSerializer(address).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


class AddressDetailView(APIView):
    def put(self, request, customer_id, pk):
        try:
            address = _svc.update_address(pk, request.data)
            return Response(WebAddressSerializer(address).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, customer_id, pk):
        try:
            _svc.delete_address(pk)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
