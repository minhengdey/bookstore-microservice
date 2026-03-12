from django.shortcuts import render, redirect
from django.conf import settings
import requests, logging

from .permissions import _role, _entity_id, require_roles, require_customer_or_staff, customer_can_only_own

logger = logging.getLogger(__name__)
SVC = settings.SERVICE_URLS


# ── Helpers ───────────────────────────────────────────────────────────────────

def _auth_headers(request) -> dict:
    """Build X-User-* headers from the validated JWT payload."""
    payload = getattr(request, "jwt_payload", None)
    if not payload:
        return {}
    return {
        "X-User-Id":   str(payload.get("user_id", "")),
        "X-User-Role": str(payload.get("role", "")),
        "X-Entity-Id": str(payload.get("entity_id", "")),
        "X-Username":  str(payload.get("username", "")),
    }


def _get(url, request=None, **kwargs):
    try:
        headers = _auth_headers(request) if request else {}
        r = requests.get(url, headers=headers, timeout=5, **kwargs)
        return r.json() if r.status_code == 200 else []
    except requests.exceptions.RequestException as e:
        logger.warning(f"[GET] {url} → {e}")
        return []


def _post(url, json=None, request=None):
    try:
        headers = _auth_headers(request) if request else {}
        return requests.post(url, json=json, headers=headers, timeout=5)
    except requests.exceptions.RequestException as e:
        logger.warning(f"[POST] {url} → {e}")
        return None


def _delete(url, request=None):
    try:
        headers = _auth_headers(request) if request else {}
        return requests.delete(url, headers=headers, timeout=5)
    except requests.exceptions.RequestException as e:
        logger.warning(f"[DELETE] {url} → {e}")
        return None


# ── Auth ─────────────────────────────────────────────────────────────────────

def login_view(request):
    """Unified login page – customers and staff/managers."""
    if request.method == "GET":
        return render(request, "login.html", {})

    username    = request.POST.get("username", "").strip()
    password    = request.POST.get("password", "")
    login_type  = request.POST.get("login_type", "customer")   # "customer" | "staff"
    error = None

    if login_type == "staff":
        url = f"{SVC['staff']}/auth/login/"
    else:
        url = f"{SVC['customer']}/auth/login/"

    try:
        r = requests.post(url, json={"username": username, "password": password}, timeout=5)
        if r.status_code == 200:
            data = r.json()
            request.session["access_token"]  = data["access"]
            request.session["refresh_token"] = data["refresh"]
            request.session["user"]          = data["user"]
            return redirect("home")
        error = r.json().get("error", "Login failed")
    except requests.exceptions.RequestException:
        error = "Auth service unavailable"

    return render(request, "login.html", {"error": error})


def logout_view(request):
    request.session.flush()
    return redirect("login")


def register_view(request):
    if request.method == "GET":
        return render(request, "register.html", {})

    payload = {
        "username": request.POST.get("username", "").strip(),
        "email":    request.POST.get("email", "").strip(),
        "password": request.POST.get("password", ""),
        "phone":    request.POST.get("phone", ""),
    }
    try:
        r = requests.post(f"{SVC['customer']}/auth/register/", json=payload, timeout=5)
        if r.status_code == 201:
            data = r.json()
            request.session["access_token"]  = data["access"]
            request.session["refresh_token"] = data["refresh"]
            request.session["user"]         = data.get("user", {})
            return redirect("home")
        error = r.json()
    except requests.exceptions.RequestException:
        error = "Customer service unavailable"

    return render(request, "register.html", {"error": error})


# ── Dashboard ─────────────────────────────────────────────────────────────────

def home(request):
    user = request.session.get("user", {})
    role = _role(request)
    # Customer: không gọi API quản lý (customers, orders full) — chỉ hiển thị theo role
    if role == "customer":
        books = _get(f"{SVC['book']}/books/", request)
        return render(request, "home.html", {
            "total_books": len(books) if isinstance(books, list) else 0,
            "total_customers": 0,
            "total_orders": 0,
            "user": user,
            "is_customer": True,
        })
    books     = _get(f"{SVC['book']}/books/",       request)
    customers = _get(f"{SVC['customer']}/customers/", request)
    orders    = _get(f"{SVC['order']}/orders/",       request)
    return render(request, "home.html", {
        "total_books":     len(books)     if isinstance(books, list)     else 0,
        "total_customers": len(customers) if isinstance(customers, list) else 0,
        "total_orders":    len(orders)    if isinstance(orders, list)    else 0,
        "user": user,
        "is_customer": False,
    })


# ── Books ─────────────────────────────────────────────────────────────────────

def book_list(request):
    role = _role(request)
    error = None
    if request.method == "POST":
        if not role:
            return redirect("login")
        if role == "customer":
            return render(request, "403.html", {"message": "Chỉ nhân viên / quản lý mới được thêm hoặc xóa sách."}, status=403)
        payload = {
            "title":      request.POST.get("title"),
            "isbn":       request.POST.get("isbn", ""),
            "list_price": request.POST.get("list_price"),
            "sale_price": request.POST.get("sale_price"),
            "stock":      request.POST.get("stock", 0),
        }
        r = _post(f"{SVC['book']}/books/", json=payload, request=request)
        if r and r.status_code == 201:
            return redirect("book_list")
        error = r.json() if r else "book-service unavailable"
    books = _get(f"{SVC['book']}/books/", request)
    return render(request, "books.html", {"books": books, "error": error, "can_manage_books": role in ("staff", "manager")})


@require_roles("staff", "manager")
def book_delete(request, book_id):
    if request.method == "POST":
        _delete(f"{SVC['book']}/books/{book_id}/", request)
    return redirect("book_list")


# ── Customers ─────────────────────────────────────────────────────────────────

@require_roles("staff", "manager")
def customer_list(request):
    error = None
    if request.method == "POST":
        payload = {
            "username": request.POST.get("username"),
            "email":    request.POST.get("email"),
            "password": request.POST.get("password"),
            "phone":    request.POST.get("phone", ""),
        }
        r = _post(f"{SVC['customer']}/customers/", json=payload, request=request)
        if r and r.status_code == 201:
            return redirect("customer_list")
        error = r.json() if r else "customer-service unavailable"
    customers = _get(f"{SVC['customer']}/customers/", request)
    return render(request, "customers.html", {"customers": customers, "error": error})


# ── Cart ──────────────────────────────────────────────────────────────────────

@require_customer_or_staff
@customer_can_only_own("customer_id")
def view_cart(request, customer_id):
    error = None
    if request.method == "POST":
        book_id  = request.POST.get("book_id")
        quantity = int(request.POST.get("quantity", 1))
        r = _post(
            f"{SVC['cart']}/carts/{customer_id}/items/",
            json={"book_id": int(book_id), "quantity": quantity},
            request=request,
        )
        if r and r.status_code == 201:
            return redirect("view_cart", customer_id=customer_id)
        error = r.json() if r else "cart-service unavailable"

    cart  = _get(f"{SVC['cart']}/carts/{customer_id}/", request)
    books = _get(f"{SVC['book']}/books/", request)
    return render(request, "cart.html", {
        "cart": cart, "customer_id": customer_id, "books": books, "error": error,
    })


# ── Checkout (Giỏ hàng → Tạo đơn hàng) ─────────────────────────────────────────

@require_customer_or_staff
@customer_can_only_own("customer_id")
def checkout(request, customer_id):
    """GET: xác nhận đơn từ giỏ. POST: tạo đơn → redirect thanh toán."""
    cart = _get(f"{SVC['cart']}/carts/{customer_id}/", request)
    items = (cart or {}).get("items") if isinstance(cart, dict) else []
    if not cart or not items:
        if request.method == "POST":
            return redirect("view_cart", customer_id=customer_id)
        return render(request, "checkout.html", {
            "customer_id": customer_id, "cart": cart or {}, "cart_items": [], "error": "Giỏ hàng trống. Thêm sản phẩm trước khi đặt hàng.",
        })

    if request.method == "POST":
        payload = {
            "customer_id": customer_id,
            "items": [{"book_id": it["book_id"], "quantity": it["quantity"], "unit_price": float(it.get("unit_price", 0))} for it in items],
            "shipping_fee": 0,
        }
        r = _post(f"{SVC['order']}/orders/", json=payload, request=request)
        if r and r.status_code in (200, 201):
            data = r.json()
            order_id = data.get("id")
            _delete(f"{SVC['cart']}/carts/{customer_id}/", request)
            return redirect("order_pay", order_id=order_id)
        err = (r.json() if r else {}).get("error") or (r.json() if r else "order-service lỗi") if r else "order-service không phản hồi"
        return render(request, "checkout.html", {
            "customer_id": customer_id, "cart": cart, "cart_items": items, "error": err,
        })

    return render(request, "checkout.html", {
        "customer_id": customer_id, "cart": cart, "cart_items": items,
    })


# ── Thanh toán đơn hàng ────────────────────────────────────────────────────────

@require_customer_or_staff
def order_pay(request, order_id):
    """GET: form chọn phương thức thanh toán. POST: gửi thanh toán."""
    order = _get(f"{SVC['order']}/orders/{order_id}/", request)
    if not order or not isinstance(order, dict):
        return render(request, "order_pay.html", {"error": "Không tìm thấy đơn hàng.", "order_id": order_id})

    if request.method == "POST":
        method_id = request.POST.get("payment_method_id")
        amount = request.POST.get("payment_amount", "").strip() or str(order.get("total_amount", 0))
        if not method_id:
            methods = _get(f"{SVC['pay']}/payment-methods/", request) or []
            return render(request, "order_pay.html", {
                "order": order, "order_id": order_id, "payment_methods": methods,
                "error": "Vui lòng chọn phương thức thanh toán.",
            })
        try:
            amount_float = float(amount)
        except ValueError:
            amount_float = float(order.get("total_amount", 0))
        r = _post(
            f"{SVC['pay']}/payments/",
            json={
                "order_id": order_id,
                "payment_amount": amount_float,
                "payment_method_id": int(method_id),
            },
            request=request,
        )
        if r and r.status_code in (200, 201):
            request.session["order_success"] = f"Đã thanh toán đơn #{order_id} thành công."
            return redirect("order_list")
        err = (r.json() if r else {}).get("error") or "Thanh toán thất bại." if r else "pay-service không phản hồi"
        methods = _get(f"{SVC['pay']}/payment-methods/", request) or []
        return render(request, "order_pay.html", {
            "order": order, "order_id": order_id, "payment_methods": methods, "error": err,
        })

    methods = _get(f"{SVC['pay']}/payment-methods/", request) or []
    return render(request, "order_pay.html", {
        "order": order, "order_id": order_id, "payment_methods": methods,
    })


# ── Orders ────────────────────────────────────────────────────────────────────

def order_list(request):
    role = _role(request)
    if not role:
        return redirect("login")
    if role == "customer":
        eid = _entity_id(request)
        if eid is not None:
            return redirect("customer_orders", customer_id=eid)
        success_msg = request.session.pop("order_success", None)
        return render(request, "orders.html", {"orders": [], "order_success_msg": success_msg})
    success_msg = request.session.pop("order_success", None)
    orders = _get(f"{SVC['order']}/orders/", request)
    return render(request, "orders.html", {"orders": orders, "can_manage": True, "order_success_msg": success_msg})


@require_customer_or_staff
@customer_can_only_own("customer_id")
def customer_orders(request, customer_id):
    success_msg = request.session.pop("order_success", None)
    orders = _get(f"{SVC['order']}/orders/", request, params={"customer_id": customer_id})
    return render(request, "orders.html", {"orders": orders, "customer_id": customer_id, "order_success_msg": success_msg})


# ── Catalog ───────────────────────────────────────────────────────────────────

def catalog_view(request):
    authors    = _get(f"{SVC['catalog']}/authors/",    request)
    categories = _get(f"{SVC['catalog']}/categories/", request)
    genres     = _get(f"{SVC['catalog']}/genres/",     request)
    publishers = _get(f"{SVC['catalog']}/publishers/", request)
    return render(request, "catalog.html", {
        "authors": authors, "categories": categories,
        "genres": genres, "publishers": publishers,
    })
