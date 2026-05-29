from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsStaffOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        ctx = getattr(request, "user_ctx", {})
        return ctx.get("role") in ["staff", "manager", "admin"]
