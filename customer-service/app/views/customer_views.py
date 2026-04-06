from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.services import CustomerService
from app.serializers import CustomerSerializer, CustomerRegisterSerializer
from app.permissions import require_staff

_svc = CustomerService()


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


class CustomerListCreateView(APIView):
    """Danh sách / tạo customer — chỉ staff/manager (đăng ký khách dùng /auth/register/)."""

    @require_staff
    def get(self, request):
        customers = _svc.list_customers()
        return Response(_paginate_and_search(request, customers, CustomerSerializer))

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
