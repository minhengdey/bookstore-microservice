from rest_framework.views import APIView
from rest_framework.response import Response
from common.auth import require_auth, require_internal
from .models import UserProfile, CustomerProfile, StaffProfile, SellerProfile, Role, UserStatus

class UserProfileView(APIView):
    @require_internal
    def get(self, request, user_id=None):
        if user_id is None:
            user_id = request.user_ctx.get("entity_id") or request.user_ctx.get("user_id")
        
        try:
            user = UserProfile.objects.prefetch_related('roles').get(auth_user_id=user_id)
            roles = list(user.roles.values_list('name', flat=True))
            data = {
                "auth_user_id": user.auth_user_id,
                "roles": roles,
                "status": user.status,
                "role_version": user.role_version,
                "full_name": user.full_name,
                "phone": user.phone,
                "gender": user.gender,
                "birthday": user.birthday,
                "avatar_url": user.avatar_url,
            }
            if "CUSTOMER" in roles:
                profile = CustomerProfile.objects.filter(user_profile=user).first()
                if profile:
                    data["loyalty_points"] = profile.loyalty_points
                    data["entity_id"] = profile.id
            if "SELLER" in roles:
                profile = SellerProfile.objects.filter(user_profile=user).first()
                if profile:
                    data["store_name"] = profile.store_name
                    data["verification_status"] = profile.verification_status
                    data["entity_id"] = profile.id
            if "STAFF" in roles or "ADMIN" in roles:
                profile = StaffProfile.objects.filter(user_profile=user).first()
                if profile:
                    data["department"] = profile.department
                    data["position"] = profile.position
                    data["entity_id"] = profile.id
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
                status=data.get("status", UserStatus.ACTIVE)
            )
            
            # Extract roles or default to CUSTOMER
            role_names = data.get("roles", ["CUSTOMER"])
            if not isinstance(role_names, list):
                role_names = [role_names]
            role_names = [r.upper() for r in role_names]
            
            roles = []
            for r_name in role_names:
                role, _ = Role.objects.get_or_create(name=r_name)
                roles.append(role)
            user.roles.set(roles)

            entity_id = None
            if "CUSTOMER" in role_names:
                p = CustomerProfile.objects.create(user_profile=user)
                entity_id = p.id
            if "SELLER" in role_names:
                p = SellerProfile.objects.create(
                    user_profile=user,
                    store_name=data.get("store_name", f"Store {user.auth_user_id}"),
                    store_slug=data.get("store_slug", f"store-{user.auth_user_id}")
                )
                if not entity_id: entity_id = p.id
            if "STAFF" in role_names or "ADMIN" in role_names:
                p = StaffProfile.objects.create(
                    user_profile=user, 
                    storage_code=data.get("storage_code", ""),
                    department=data.get("department", ""),
                    position=data.get("position", "")
                )
                if not entity_id: entity_id = p.id
            return Response({"id": user.auth_user_id, "auth_user_id": user.auth_user_id, "roles": role_names, "entity_id": entity_id}, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

    @require_internal
    def delete(self, request, user_id=None):
        try:
            UserProfile.objects.filter(auth_user_id=user_id).first().delete()
            return Response(status=204)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

class PublicUserProfileView(APIView):
    @require_auth
    def get(self, request):
        user_id = request.user_id
        try:
            user = UserProfile.objects.prefetch_related('roles').get(auth_user_id=user_id)
            roles = list(user.roles.values_list('name', flat=True))
            data = {
                "auth_user_id": user.auth_user_id,
                "roles": roles,
                "status": user.status,
                "full_name": user.full_name,
                "phone": user.phone,
                "gender": user.gender,
                "birthday": user.birthday,
                "avatar_url": user.avatar_url,
            }
            if "CUSTOMER" in roles:
                profile = CustomerProfile.objects.filter(user_profile=user).first()
                if profile:
                    data["loyalty_points"] = profile.loyalty_points
                    data["entity_id"] = profile.id
            if "SELLER" in roles:
                profile = SellerProfile.objects.filter(user_profile=user).first()
                if profile:
                    data["store_name"] = profile.store_name
                    data["verification_status"] = profile.verification_status
                    data["entity_id"] = profile.id
            if "STAFF" in roles or "ADMIN" in roles:
                profile = StaffProfile.objects.filter(user_profile=user).first()
                if profile:
                    data["department"] = profile.department
                    data["position"] = profile.position
                    data["entity_id"] = profile.id
            return Response(data)
        except UserProfile.DoesNotExist:
            return Response({"error": "UserProfile not found"}, status=404)
