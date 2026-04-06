from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.services import CustomerService
from app.serializers import WebAddressSerializer

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


class AddressListCreateView(APIView):
    def get(self, request, customer_id):
        try:
            addresses = _svc.list_addresses(customer_id)
            return Response(_paginate_and_search(request, addresses, WebAddressSerializer))
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
