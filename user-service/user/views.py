from rest_framework.views import APIView
from rest_framework.response import Response
from common.auth import require_auth, require_internal
from .models import UserProfile, CustomerProfile, StaffProfile

class UserProfileView(APIView):
    @require_internal
    def get(self, request, user_id=None):
        if user_id is None:
            user_id = request.user_ctx.get("entity_id") or request.user_ctx.get("user_id")
        
        try:
            user = UserProfile.objects.get(auth_user_id=user_id)
            data = {
                "auth_user_id": user.auth_user_id,
                "role": user.role,
                "full_name": user.full_name,
                "phone": user.phone,
                "gender": user.gender,
                "birthday": user.birthday,
                "avatar_url": user.avatar_url,
            }
            if user.role == "customer":
                profile = CustomerProfile.objects.filter(user_profile=user).first()
                if profile:
                    data["loyalty_points"] = profile.loyalty_points
            else:
                profile = StaffProfile.objects.filter(user_profile=user).first()
                if profile:
                    data["department"] = profile.department
                    data["position"] = profile.position
            return Response(data)
        except UserProfile.DoesNotExist:
            return Response({"error": "UserProfile not found"}, status=404)

    @require_internal
    def post(self, request, user_id=None):
        data = request.data
        try:
            user = UserProfile.objects.create(
                auth_user_id=data["auth_user_id"],
                full_name=data.get("full_name", ""),
                phone=data.get("phone", ""),
                role=data.get("role", "customer")
            )
            if user.role == "customer":
                CustomerProfile.objects.create(user_profile=user)
            else:
                StaffProfile.objects.create(
                    user_profile=user, 
                    storage_code=data.get("storage_code", ""),
                    department=data.get("department", ""),
                    position=data.get("position", "")
                )
            return Response({"id": user.auth_user_id, "auth_user_id": user.auth_user_id}, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

    @require_internal
    def delete(self, request, user_id=None):
        try:
            # This handles soft delete since we defined delete() in SoftDeleteModel
            UserProfile.objects.filter(auth_user_id=user_id).first().delete()
            return Response(status=204)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

class PublicUserProfileView(APIView):
    @require_auth
    def get(self, request):
        user_id = request.user_id
        try:
            user = UserProfile.objects.get(auth_user_id=user_id)
            data = {
                "auth_user_id": user.auth_user_id,
                "role": user.role,
                "full_name": user.full_name,
                "phone": user.phone,
                "gender": user.gender,
                "birthday": user.birthday,
                "avatar_url": user.avatar_url,
            }
            if user.role == "customer":
                profile = CustomerProfile.objects.filter(user_profile=user).first()
                if profile:
                    data["loyalty_points"] = profile.loyalty_points
            else:
                profile = StaffProfile.objects.filter(user_profile=user).first()
                if profile:
                    data["department"] = profile.department
                    data["position"] = profile.position
            return Response(data)
        except UserProfile.DoesNotExist:
            return Response({"error": "UserProfile not found"}, status=404)
