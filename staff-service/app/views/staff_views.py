from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.services import StaffService
from app.serializers import InventoryStaffSerializer, StaffCreateSerializer
from app.permissions import require_staff, require_manager

_svc = StaffService()


class StaffListCreateView(APIView):
    @require_staff
    def get(self, request):
        return Response(InventoryStaffSerializer(_svc.list_staff(), many=True).data)

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
