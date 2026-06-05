from rest_framework.permissions import BasePermission
import redis
import json

redis_client = redis.StrictRedis.from_url('redis://redis:6379/0', decode_responses=True)

class IsAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return bool(getattr(request, "user_ctx", None))

class HasPermission(BasePermission):
    required_permission = None

    def has_permission(self, request, view):
        if not self.required_permission:
            return True
        
        ctx = getattr(request, "user_ctx", {})
        user_id = ctx.get("user_id") or ctx.get("entity_id")
        if not user_id:
            return False

        # First check roles if SUPER_ADMIN
        roles = ctx.get("roles", [])
        if "SUPER_ADMIN" in roles:
            return True

        # Check permission cache
        cache_key = f"user_permissions:v1:{user_id}"
        permissions = redis_client.get(cache_key)
        if permissions:
            perms_list = json.loads(permissions)
            return self.required_permission in perms_list

        # If not in cache, fallback to checking DB (not ideal for perf but needed if cache miss)
        # Note: in real implementation, should fetch from DB and populate cache here
        from .models import UserProfile
        try:
            user = UserProfile.objects.prefetch_related('roles__permissions').get(auth_user_id=user_id)
            user_perms = set()
            for role in user.roles.all():
                for perm in role.permissions.all():
                    user_perms.add(perm.code)
            
            # Cache it
            redis_client.setex(cache_key, 300, json.dumps(list(user_perms))) # 5 min TTL
            return self.required_permission in user_perms
        except Exception:
            return False

class IsOwnerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(getattr(request, "user_ctx", None))

    def has_object_permission(self, request, view, obj):
        ctx = getattr(request, "user_ctx", {})
        roles = ctx.get("roles", [])
        if "ADMIN" in roles or "SUPER_ADMIN" in roles:
            return True
        # Assuming obj has auth_user_id or user_id or id
        obj_id = getattr(obj, 'auth_user_id', getattr(obj, 'id', None))
        return str(obj_id) == str(ctx.get("entity_id") or ctx.get("user_id"))
