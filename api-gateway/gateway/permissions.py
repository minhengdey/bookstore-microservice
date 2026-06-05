"""
Phân quyền tại API Gateway (UI).
- customer: chỉ xem sách, catalog, giỏ hàng của mình, đơn hàng của mình; không quản lý.
- staff / manager: quản lý sách, catalog, xem danh sách khách, đơn hàng.
"""
from functools import wraps
from django.shortcuts import redirect, render


def _user(request):
    return request.session.get("user") or {}


def _roles(request):
    roles = _user(request).get("roles", [])
    if isinstance(roles, str):
        roles = [roles]
    return [r.strip().upper() for r in roles]


def _role(request):
    # Compatibility helper for existing views
    roles = _roles(request)
    if not roles:
        return ""
    if "CUSTOMER" in roles and len(roles) == 1:
        return "customer"
    if "STAFF" in roles:
        return "staff"
    if "ADMIN" in roles or "SUPER_ADMIN" in roles:
        return "manager"
    if "CUSTOMER" in roles:
        return "customer"
    return roles[0].lower()


def _entity_id(request):
    eid = _user(request).get("entity_id")
    if eid is not None:
        try:
            return int(eid)
        except (TypeError, ValueError):
            pass
    return None


def require_roles(*allowed_roles):
    """Chỉ cho phép các role trong allowed_roles (staff, manager). Customer bị chặn."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            roles = _roles(request)
            if not roles:
                return redirect("login")
            
            allowed = [r.upper() for r in allowed_roles]
            if "MANAGER" in allowed:
                allowed.extend(["ADMIN", "SUPER_ADMIN"])
                
            has_permission = any(r in allowed for r in roles)
            if not has_permission:
                return render(request, "403.html", {"message": "Bạn không có quyền truy cập trang này."}, status=403)
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


def require_customer_or_staff(view_func):
    """Customer chỉ truy cập được dữ liệu của chính mình (kiểm tra ở view). Staff/manager được phép."""
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not _roles(request):
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return wrapped


def customer_can_only_own(customer_id_param="customer_id"):
    """Decorator: nếu là customer thì kwargs[customer_id_param] phải bằng entity_id của session."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            roles = _roles(request)
            if not roles:
                return redirect("login")
            
            # If they are ONLY a customer
            if "CUSTOMER" in roles and "STAFF" not in roles and "ADMIN" not in roles and "SUPER_ADMIN" not in roles:
                eid = _entity_id(request)
                cid = kwargs.get(customer_id_param)
                try:
                    cid = int(cid) if cid is not None else None
                except (TypeError, ValueError):
                    cid = None
                if eid is None or cid != eid:
                    return render(request, "403.html", {"message": "Bạn chỉ được xem giỏ hàng / đơn hàng của mình."}, status=403)
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator
