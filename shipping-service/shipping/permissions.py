from rest_framework.permissions import BasePermission

class IsShippingOwner(BasePermission):
    def has_permission(self, request, view):
        return bool(getattr(request, "user_ctx", None))

    def has_object_permission(self, request, view, obj):
        ctx = getattr(request, "user_ctx", {})
        if ctx.get("role") in ["staff", "manager", "admin"]:
            return True
        return True
