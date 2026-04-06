from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.services import StaffService
from app.serializers import InventoryStaffSerializer, StaffCreateSerializer
from app.permissions import require_staff, require_manager

_svc = StaffService()


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


class StaffListCreateView(APIView):
    @require_staff
    def get(self, request):
        return Response(_paginate_and_search(request, _svc.list_staff(), InventoryStaffSerializer))

    @require_manager
    def post(self, request):
        ser = StaffCreateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        d = ser.validated_data
        user_data  = {k: d[k] for k in ("username", "email", "password") if k in d}
        if "phone" in d:
            user_data["phone"] = d["phone"]
        staff_data = {k: d[k] for k in ("storage_code", "department", "position", "role") if k in d}
        try:
            staff = _svc.create_staff(user_data, staff_data)
            return Response(InventoryStaffSerializer(staff).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StaffDetailView(APIView):
    @require_staff
    def get(self, request, pk):
        try:
            return Response(InventoryStaffSerializer(_svc.get_staff(pk)).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    @require_manager
    def put(self, request, pk):
        try:
            staff = _svc.update_staff(pk, request.data)
            return Response(InventoryStaffSerializer(staff).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    @require_manager
    def delete(self, request, pk):
        try:
            _svc.delete_staff(pk)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
