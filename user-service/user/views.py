from rest_framework.views import APIView
from rest_framework.response import Response
from common.auth import require_auth, require_internal
from .models import UserProfile, CustomerProfile, StaffProfile, SellerProfile, Role, UserStatus, WebAddress

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

class CustomerListView(APIView):
    @require_internal
    def get(self, request):
        customers = CustomerProfile.objects.select_related("user_profile").prefetch_related(
            "user_profile__roles"
        ).all()
        results = []
        for cp in customers:
            user = cp.user_profile
            roles = list(user.roles.values_list("name", flat=True))
            results.append({
                "id": cp.id,
                "entity_id": cp.id,
                "auth_user_id": str(user.auth_user_id),
                "full_name": user.full_name,
                "phone": user.phone,
                "status": user.status,
                "roles": roles,
                "loyalty_points": cp.loyalty_points,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            })
        return Response(results)


class CustomerDetailView(APIView):
    @require_internal
    def get(self, request, customer_id):
        try:
            cp = CustomerProfile.objects.select_related("user_profile").prefetch_related(
                "user_profile__roles"
            ).get(pk=customer_id)
        except CustomerProfile.DoesNotExist:
            return Response({"error": "Customer not found"}, status=404)
        user = cp.user_profile
        roles = list(user.roles.values_list("name", flat=True))
        return Response({
            "id": cp.id,
            "entity_id": cp.id,
            "auth_user_id": str(user.auth_user_id),
            "full_name": user.full_name,
            "phone": user.phone,
            "status": user.status,
            "roles": roles,
            "loyalty_points": cp.loyalty_points,
            "gender": user.gender,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        })


class AddressListView(APIView):
    @require_internal
    def get(self, request, user_id):
        profile = CustomerProfile.objects.filter(user_profile__auth_user_id=user_id).first()
        if not profile:
            return Response([])
        addresses = WebAddress.objects.filter(customer=profile).order_by('-is_default', '-id').values(
            "id", "recipient_name", "address_line", "city", "state", "country", "postal_code", "phone", "is_default"
        )
        return Response(list(addresses))

    @require_internal
    def post(self, request, user_id):
        profile = CustomerProfile.objects.filter(user_profile__auth_user_id=user_id).first()
        if not profile:
            return Response({"error": "Customer profile not found"}, status=404)
        
        data = request.data
        required = {
            "recipient_name": "Tên người nhận",
            "phone": "Số điện thoại",
            "address_line": "Địa chỉ",
            "city": "Thành phố",
        }
        for field, label in required.items():
            if not str(data.get(field) or "").strip():
                return Response({"error": f"{label} là bắt buộc."}, status=400)

        is_default = str(data.get("is_default")).lower() in ('true', '1')
        
        if not WebAddress.objects.filter(customer=profile).exists():
            is_default = True
            
        if is_default:
            WebAddress.objects.filter(customer=profile).update(is_default=False)
            
        addr = WebAddress.objects.create(
            customer=profile,
            recipient_name=data.get("recipient_name", ""),
            address_line=data.get("address_line", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            country=data.get("country", ""),
            postal_code=data.get("postal_code", ""),
            phone=data.get("phone", ""),
            is_default=is_default
        )
        return Response({"id": addr.id}, status=201)

class AddressDetailView(APIView):
    @require_internal
    def put(self, request, user_id, address_id):
        profile = CustomerProfile.objects.filter(user_profile__auth_user_id=user_id).first()
        addr = WebAddress.objects.filter(customer=profile, id=address_id).first()
        if not addr: return Response(status=404)
        
        data = request.data
        if "is_default" in data:
            is_default = str(data.get("is_default")).lower() in ('true', '1')
            if is_default:
                WebAddress.objects.filter(customer=profile).update(is_default=False)
                addr.is_default = True
            
        addr.recipient_name = data.get("recipient_name", addr.recipient_name)
        addr.address_line = data.get("address_line", addr.address_line)
        addr.city = data.get("city", addr.city)
        addr.phone = data.get("phone", addr.phone)
        addr.save()
        return Response({"status": "success"})

    @require_internal
    def delete(self, request, user_id, address_id):
        profile = CustomerProfile.objects.filter(user_profile__auth_user_id=user_id).first()
        WebAddress.objects.filter(customer=profile, id=address_id).delete()
        return Response(status=204)
