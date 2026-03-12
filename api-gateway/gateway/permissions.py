"""
Phân quyền tại API Gateway (UI).
- customer: chỉ xem sách, catalog, giỏ hàng của mình, đơn hàng của mình; không quản lý.
- staff / manager: quản lý sách, catalog, xem danh sách khách, đơn hàng.
"""
from functools import wraps
from django.shortcuts import redirect, render


def _user(request):
    return request.session.get("user") or {}


def _role(request):
    return (_user(request).get("role") or "").strip().lower()


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
            role = _role(request)
            if not role:
                return redirect("login")
            if role not in allowed_roles:
                return render(request, "403.html", {"message": "Bạn không có quyền truy cập trang này."}, status=403)
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


def require_customer_or_staff(view_func):
    """Customer chỉ truy cập được dữ liệu của chính mình (kiểm tra ở view). Staff/manager được phép."""
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        role = _role(request)
        if not role:
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return wrapped


def customer_can_only_own(customer_id_param="customer_id"):
    """Decorator: nếu là customer thì kwargs[customer_id_param] phải bằng entity_id của session."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            role = _role(request)
            if not role:
                return redirect("login")
            if role == "customer":
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
