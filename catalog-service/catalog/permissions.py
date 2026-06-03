from rest_framework import permissions

class IsCatalogAdmin(permissions.BasePermission):
    """
    Custom permission to only allow admins to edit catalog items.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        # For this microservice, assume request.user is set via JWT middleware,
        # or we check headers like X-User-Role == 'ADMIN'
        role = request.META.get('HTTP_X_USER_ROLE', 'CUSTOMER')
        return role == 'ADMIN'
