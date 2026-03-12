from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.services import CustomerService
from app.serializers import CustomerSerializer, CustomerRegisterSerializer
from app.permissions import require_staff

_svc = CustomerService()


class CustomerListCreateView(APIView):
    """Danh sách / tạo customer — chỉ staff/manager (đăng ký khách dùng /auth/register/)."""

    @require_staff
    def get(self, request):
        customers = _svc.list_customers()
        return Response(CustomerSerializer(customers, many=True).data)

    @require_staff
    def post(self, request):
        ser = CustomerRegisterSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            customer = _svc.register_customer(user_data=dict(ser.validated_data))
            return Response(CustomerSerializer(customer).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CustomerDetailView(APIView):
    @require_staff
    def get(self, request, pk):
        try:
            customer = _svc.get_customer(pk)
            return Response(CustomerSerializer(customer).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    @require_staff
    def put(self, request, pk):
        try:
            customer = _svc.update_customer(pk, request.data)
            return Response(CustomerSerializer(customer).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    @require_staff
    def delete(self, request, pk):
        try:
            _svc.delete_customer(pk)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
