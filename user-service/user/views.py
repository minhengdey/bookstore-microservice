from rest_framework.views import APIView
from rest_framework.response import Response
from common.auth import require_auth, require_internal
from .models import User, CustomerProfile, StaffProfile

class UserProfileView(APIView):
    @require_internal
    def get(self, request, user_id=None):
        if user_id is None:
            user_id = request.user_ctx["entity_id"]
        
        try:
            user = User.objects.get(id=user_id)
            data = {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "username": user.username,
                "phone": user.phone,
            }
            if user.role == "customer":
                profile = CustomerProfile.objects.filter(user=user).first()
                if profile:
                    data["loyalty_points"] = profile.loyalty_points
            else:
                profile = StaffProfile.objects.filter(user=user).first()
                if profile:
                    data["department"] = profile.department
                    data["position"] = profile.position
            return Response(data)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

    @require_internal
    def post(self, request, user_id=None):
        # Create user from auth-service
        data = request.data
        try:
            user = User.objects.create(
                id=data["id"],
                username=data["username"],
                email=data["email"],
                phone=data.get("phone", ""),
                role=data.get("role", "customer")
            )
            if user.role == "customer":
                CustomerProfile.objects.create(user=user)
            else:
                StaffProfile.objects.create(
                    user=user, 
                    storage_code=data.get("storage_code", ""),
                    department=data.get("department", ""),
                    position=data.get("position", "")
                )
            return Response({"id": user.id}, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

    @require_internal
    def delete(self, request, user_id=None):
        try:
            User.objects.filter(id=user_id).delete()
            return Response(status=204)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

class PublicUserProfileView(APIView):
    @require_auth
    def get(self, request):
        user_id = request.user_id
        try:
            user = User.objects.get(id=user_id)
            data = {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "username": user.username,
                "phone": user.phone,
            }
            if user.role == "customer":
                profile = CustomerProfile.objects.filter(user=user).first()
                if profile:
                    data["loyalty_points"] = profile.loyalty_points
            else:
                profile = StaffProfile.objects.filter(user=user).first()
                if profile:
                    data["department"] = profile.department
                    data["position"] = profile.position
            return Response(data)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
