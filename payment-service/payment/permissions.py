from rest_framework.permissions import BasePermission

class IsPaymentOwner(BasePermission):
    def has_permission(self, request, view):
        return bool(getattr(request, "user_ctx", None))

    def has_object_permission(self, request, view, obj):
        ctx = getattr(request, "user_ctx", {})
        if ctx.get("role") in ["staff", "manager", "admin"]:
            return True
        # NOTE: If payment has customer_id, check it here. Otherwise, may need to fetch from order-service.
        return True
