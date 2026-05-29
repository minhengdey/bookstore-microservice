from django.shortcuts import render, redirect
from django.conf import settings
import requests, logging
import time
from urllib.parse import urlencode
from collections import defaultdict

from .permissions import _role, _entity_id, require_roles, require_customer_or_staff, customer_can_only_own

logger = logging.getLogger(__name__)
SVC = settings.SERVICE_URLS

# Simple request cache
_req_cache = {}
_req_cache_ttl = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _list_data(payload):
    """
    Chuẩn hóa dữ liệu list trả về từ service:
    - API cũ: trả list trực tiếp
    - API mới: trả object phân trang có key `results`
    """
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        return payload["results"]
    return []


def _total_count(payload):
    if isinstance(payload, dict):
        try:
            return int(payload.get("count", 0))
        except (TypeError, ValueError):
            return 0
    if isinstance(payload, list):
        return len(payload)
    return 0


def _list_query_params(request):
    params = {}
    page = request.GET.get("page")
    page_size = request.GET.get("page_size")
    search = request.GET.get("search")
    category_id = request.GET.get("category_id")
    if page:
        params["page"] = page
    if page_size:
        params["page_size"] = page_size
    if search:
        params["search"] = search
    if category_id:
        params["category_id"] = category_id
    return params


def _pagination_context(payload, request, extra_query=None):
    if not isinstance(payload, dict):
        return {
            "count": len(payload) if isinstance(payload, list) else 0,
            "page": 1,
            "page_size": 10,
            "total_pages": 1,
            "next_page": None,
            "prev_page": None,
            "search": request.GET.get("search", ""),
            "query_for_prev": "",
            "query_for_next": "",
        }

    page_size = payload.get("page_size", 10)
    search = request.GET.get("search", "")
    prev_page = payload.get("prev_page")
    next_page = payload.get("next_page")
    base_params = {"page_size": page_size}
    if extra_query:
        base_params.update(extra_query)
    if search:
        base_params["search"] = search
    base = urlencode(base_params)
    return {
        "count": payload.get("count", 0),
        "page": payload.get("page", 1),
        "page_size": page_size,
        "total_pages": payload.get("total_pages", 1),
        "next_page": next_page,
        "prev_page": prev_page,
        "search": search,
        "query_for_prev": f"?page={prev_page}&{base}" if prev_page else "",
        "query_for_next": f"?page={next_page}&{base}" if next_page else "",
    }

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


def _get(url, request=None, cache_ttl=0, **kwargs):
    """GET with optional caching. cache_ttl in seconds (0=no cache)."""
    # Check cache
    now = time.time()
    if cache_ttl > 0 and url in _req_cache:
        if now < _req_cache_ttl.get(url, 0):
            logger.debug(f"[CACHE HIT] {url}")
            return _req_cache[url]
    
    try:
        headers = _auth_headers(request) if request else {}
        r = requests.get(url, headers=headers, timeout=60, **kwargs)
        result = r.json() if r.status_code == 200 else []
        
        # Cache if requested
        if cache_ttl > 0:
            _req_cache[url] = result
            _req_cache_ttl[url] = now + cache_ttl
            logger.debug(f"[CACHE SET] {url} for {cache_ttl}s")
        
        return result
    except requests.exceptions.RequestException as e:
        logger.warning(f"[GET] {url} → {e}")
        # Return cached value if available, even if expired
        if url in _req_cache:
            logger.warning(f"[FALLBACK TO STALE CACHE] {url}")
            return _req_cache[url]
        return []


def _post(url, json=None, request=None):
    try:
        headers = _auth_headers(request) if request else {}
        return requests.post(url, json=json, headers=headers, timeout=5)
    except requests.exceptions.RequestException as e:
        logger.warning(f"[POST] {url} → {e}")
        return None


def _response_error(response, unavailable_message):
    if response is None:
        return unavailable_message
    try:
        return response.json()
    except ValueError:
        return response.text or f"HTTP {response.status_code}"


def _delete(url, request=None):
    try:
        headers = _auth_headers(request) if request else {}
        return requests.delete(url, headers=headers, timeout=5)
    except requests.exceptions.RequestException as e:
        logger.warning(f"[DELETE] {url} → {e}")
        return None


def _client_device(request):
    user_agent = (request.META.get("HTTP_USER_AGENT") or "").lower()
    if "mobile" in user_agent or "android" in user_agent or "iphone" in user_agent:
        return "mobile"
    if "ipad" in user_agent or "tablet" in user_agent:
        return "tablet"
    return "desktop"


def _track_behavior_event(request, customer_id, product_id, action):
    if customer_id is None:
        return
    if not request.session.session_key:
        request.session.create()
    try:
        headers = _auth_headers(request)
        requests.post(
            f"{SVC['recommender']}/api/recommender/events/",
            json={
                "customer_id": int(customer_id),
                "product_id": int(product_id),
                "action": action,
                "session_id": request.session.session_key,
                "device": _client_device(request),
                "persona": _role(request) or "anonymous",
            },
            headers=headers,
            timeout=0.5,
        )
    except (TypeError, ValueError, requests.exceptions.RequestException) as e:
        logger.debug("[behavior] skipped action=%s product=%s: %s", action, product_id, e)


def _catalog_name_map(request, endpoint, field_name):
    payload = _get(f"{SVC['product']}/{endpoint}/", request, params={"page_size": 200})
    items = _list_data(payload)
    result = {}
    for item in items:
        item_id = item.get("id")
        label = item.get(field_name)
        if item_id is not None and label:
            result[int(item_id)] = label
    return result


def _hydrate_book_catalog_data(request, book):
    author_map = _catalog_name_map(request, "authors", "author_name")
    genre_map = _catalog_name_map(request, "genres", "genre_name")
    publisher_map = _catalog_name_map(request, "publishers", "publisher_name")
    category_map = _catalog_name_map(request, "categories", "category_name")
    return {
        "authors": [author_map.get(int(i), f"Author #{i}") for i in book.get("author_ids", [])],
        "genres": [genre_map.get(int(i), f"Genre #{i}") for i in book.get("genre_ids", [])],
        "publishers": [publisher_map.get(int(i), f"Publisher #{i}") for i in book.get("publisher_ids", [])],
        "categories": [category_map.get(int(i), f"Category #{i}") for i in book.get("category_ids", [])],
    }


def _recommendation_products(request, customer_id, limit=6):
    payload = _get(f"{SVC['recommender']}/recommendations/{customer_id}/", request, params={"limit": limit})
    if not isinstance(payload, dict):
        return []
    ids = payload.get("recommended_product_ids") or payload.get("recommended_book_ids") or []
    products = []
    for pid in ids:
        data = _get(f"{SVC['product']}/products/{pid}/", request)
        if isinstance(data, dict) and data.get("id"):
            products.append(data)
    return products


# ── Auth ─────────────────────────────────────────────────────────────────────

def login_view(request):
    """Unified login page – customers and staff/managers."""
    if request.method == "GET":
        return render(request, "login.html", {})

    username    = request.POST.get("username", "").strip()
    password    = request.POST.get("password", "")
    login_type  = request.POST.get("login_type", "customer")   # "customer" | "staff"
    error = None

    url = f"{SVC['auth']}/auth/login/"

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
        "role":     "customer"
    }
    try:
        r = requests.post(f"{SVC['auth']}/auth/register/", json=payload, timeout=5)
        if r.status_code == 201:
            data = r.json()
            request.session["access_token"]  = data["access"]
            request.session["refresh_token"] = data["refresh"]
            request.session["user"]         = data.get("user", {})
            return redirect("home")
        error = r.json()
    except requests.exceptions.RequestException:
        error = "Auth service unavailable"

    return render(request, "register.html", {"error": error})


# ── Dashboard ─────────────────────────────────────────────────────────────────

def home(request):
    user = request.session.get("user", {})
    role = _role(request)
    eid = _entity_id(request)

    # Common data - cache product list for 10s to avoid repeated slow calls
    products_payload = _get(f"{SVC['product']}/products/", request, cache_ttl=10)
    total_products = _total_count(products_payload)

    if role == "customer":
        # Get AI recommendations for home page
        recommendations = _recommendation_products(request, eid, limit=5) if eid else []
        return render(request, "home.html", {
            "total_products": total_products,
            "total_customers": 0,
            "total_orders": 0,
            "user": user,
            "is_customer": True,
            "recommendations": recommendations,
        })

    if role not in ("staff", "manager"):
        return render(request, "home.html", {
            "total_products": total_products,
            "total_customers": 0,
            "total_orders": 0,
            "user": user,
            "is_customer": False,
        })

    # Cache order list for 10s
    orders_payload = _get(f"{SVC['order']}/orders/", request, cache_ttl=10)
    return render(request, "home.html", {
        "total_products": total_products,
        "total_customers": 0,
        "total_orders": _total_count(orders_payload),
        "user": user,
        "is_customer": False,
    })


# ── Books ─────────────────────────────────────────────────────────────────────

def product_list(request):
    role = _role(request)
    error = None
    if request.method == "POST":
        if not role:
            return redirect("login")
        if role == "customer":
            return render(request, "403.html", {"message": "Chỉ nhân viên / quản lý mới được thêm hoặc xóa sản phẩm."}, status=403)
        payload = {
            "name":      request.POST.get("name"),
            "sku":       request.POST.get("sku", ""),
            "price":     request.POST.get("price"),
            "category_id": request.POST.get("category_id"),
        }
        r = _post(f"{SVC['product']}/products/", json=payload, request=request)
        if r is not None and r.status_code == 201:
            return redirect("product_list")
        error = _response_error(r, "product-service unavailable")
    products_payload = _get(f"{SVC['product']}/products/", request, params=_list_query_params(request))
    products_pagination = _pagination_context(products_payload, request)
    categories_payload = _get(f"{SVC['product']}/categories/", request, params={"page_size": 100})
    categories = _list_data(categories_payload)
    search_query = request.GET.get("search", "").strip()
    if role == "customer" and search_query:
        customer_id = _entity_id(request)
        for product in _list_data(products_payload)[:5]:
            product_id = product.get("id") if isinstance(product, dict) else None
            if product_id is not None:
                _track_behavior_event(request, customer_id, product_id, "search")
    return render(request, "products.html", {
        "products": _list_data(products_payload),
        "products_pagination": products_pagination,
        "categories": categories,
        "search_query": search_query,
        "category_id": request.GET.get("category_id", ""),
        "error": error,
        "can_manage_products": role in ("staff", "manager"),
    })


def product_detail(request, product_id):
    role = _role(request)
    customer_id = _entity_id(request) if role == "customer" else None
    product = _get(f"{SVC['product']}/products/{product_id}/", request)
    if not isinstance(product, dict) or not product.get("id"):
        return render(request, "403.html", {"message": "Không tìm thấy sản phẩm."}, status=404)

    error = None
    if request.method == "POST":
        if customer_id is None:
            return redirect("login")
        quantity = int(request.POST.get("quantity", 1))
        r = _post(
            f"{SVC['cart']}/carts/{customer_id}/items/",
            json={"product_id": int(product_id), "quantity": quantity},
            request=request,
        )
        if r is not None and r.status_code == 201:
            _track_behavior_event(request, customer_id, product_id, "add_to_cart")
            return redirect("view_cart", customer_id=customer_id)
        error = _response_error(r, "cart-service unavailable")

    if customer_id is not None:
        _track_behavior_event(request, customer_id, product_id, "click")
        _track_behavior_event(request, customer_id, product_id, "view")

    recommendations = _recommendation_products(request, customer_id, limit=6) if customer_id else []
    return render(request, "product_detail.html", {
        "product": product,
        "recommendations": recommendations,
        "is_customer": role == "customer",
        "customer_id": customer_id,
        "error": error,
    })


@require_roles("staff", "manager")
def product_delete(request, product_id):
    if request.method == "POST":
        _delete(f"{SVC['product']}/products/{product_id}/", request)
    return redirect("product_list")





# ── Cart ──────────────────────────────────────────────────────────────────────

@require_customer_or_staff
@customer_can_only_own("customer_id")
def view_cart(request, customer_id):
    error = None
    if request.method == "POST":
        action = request.POST.get("action", "add")
        product_id = request.POST.get("product_id") or request.POST.get("book_id")
        if action == "remove":
            if product_id:
                r = _delete(f"{SVC['cart']}/carts/{customer_id}/items/{int(product_id)}/", request)
                if r is not None and r.status_code in (200, 204):
                    if _role(request) == "customer":
                        _track_behavior_event(request, customer_id, int(product_id), "remove_from_cart")
            return redirect("view_cart", customer_id=customer_id)
        quantity = int(request.POST.get("quantity", 1))
        if not product_id:
            return render(request, "cart.html", {
                "cart": _get(f"{SVC['cart']}/carts/{customer_id}/", request),
                "customer_id": customer_id,
                "products": _list_data(_get(f"{SVC['product']}/products/", request, params={"page_size": 500})),
                "error": "Vui lòng chọn sản phẩm.",
            })
        r = _post(
            f"{SVC['cart']}/carts/{customer_id}/items/",
            json={"product_id": int(product_id), "quantity": quantity},
            request=request,
        )
        if r is not None and r.status_code == 201:
            if _role(request) == "customer":
                _track_behavior_event(request, customer_id, int(product_id), "add_to_cart")
            return redirect("view_cart", customer_id=customer_id)
        error = _response_error(r, "cart-service unavailable")

    cart = _get(f"{SVC['cart']}/carts/{customer_id}/", request)
    products_payload = _get(f"{SVC['product']}/products/", request, params={"page_size": 500})
    product_map = {b.get("id"): b for b in _list_data(products_payload) if isinstance(b, dict) and b.get("id") is not None}

    cart_items = []
    for item in (cart or {}).get("items", []):
        bid = item.get("product_id", item.get("book_id"))
        product = product_map.get(bid, {})
        unit_price = float(item.get("unit_price") or 0)
        qty = int(item.get("quantity") or 0)
        cart_items.append({
            **item,
            "product_name": product.get("name") or f"Sản phẩm #{bid}",
            "line_total": unit_price * qty,
        })

    if isinstance(cart, dict):
        cart["items"] = cart_items

    return render(request, "cart.html", {
        "cart": cart, "customer_id": customer_id, "products": _list_data(products_payload), "error": error,
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
            "items": [{"product_id": it["product_id"], "quantity": it["quantity"], "unit_price": float(it.get("unit_price", 0))} for it in items],
            "shipping_fee": 0,
        }
        r = _post(f"{SVC['order']}/orders/", json=payload, request=request)
        if r is not None and r.status_code in (200, 201):
            data = r.json()
            order_id = data.get("id")
            _delete(f"{SVC['cart']}/carts/{customer_id}/", request)
            return redirect("order_pay", order_id=order_id)
        err_payload = _response_error(r, "order-service không phản hồi")
        err = err_payload.get("error") if isinstance(err_payload, dict) else err_payload
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
            methods_payload = _get(f"{SVC['pay']}/payment-methods/", request) or []
            return render(request, "order_pay.html", {
                "order": order, "order_id": order_id, "payment_methods": _list_data(methods_payload),
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
        if r is not None and r.status_code in (200, 201):
            request.session["order_success"] = f"Đã thanh toán đơn #{order_id} thành công."
            if _role(request) == "customer":
                customer_id = order.get("customer_id")
                for item in order.get("items", []):
                    product_id = item.get("product_id") if isinstance(item, dict) else None
                    if product_id is not None:
                        _track_behavior_event(request, customer_id, int(product_id), "purchase")
            return redirect("order_list")
        err_payload = _response_error(r, "pay-service không phản hồi")
        err = err_payload.get("error") if isinstance(err_payload, dict) else err_payload
        methods_payload = _get(f"{SVC['pay']}/payment-methods/", request) or []
        return render(request, "order_pay.html", {
            "order": order, "order_id": order_id, "payment_methods": _list_data(methods_payload), "error": err,
        })

    methods_payload = _get(f"{SVC['pay']}/payment-methods/", request) or []
    return render(request, "order_pay.html", {
        "order": order, "order_id": order_id, "payment_methods": _list_data(methods_payload),
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
    orders_payload = _get(f"{SVC['order']}/orders/", request, params=_list_query_params(request))
    return render(request, "orders.html", {
        "orders": _list_data(orders_payload),
        "orders_pagination": _pagination_context(orders_payload, request),
        "can_manage": True,
        "order_success_msg": success_msg,
    })


@require_customer_or_staff
@customer_can_only_own("customer_id")
def customer_orders(request, customer_id):
    success_msg = request.session.pop("order_success", None)
    params = _list_query_params(request)
    params["customer_id"] = customer_id
    orders_payload = _get(f"{SVC['order']}/orders/", request, params=params)
    return render(request, "orders.html", {
        "orders": _list_data(orders_payload),
        "orders_pagination": _pagination_context(orders_payload, request),
        "customer_id": customer_id,
        "order_success_msg": success_msg,
    })


# ── Recommendations ───────────────────────────────────────────────────────────

@require_customer_or_staff
def recommendation_list(request):
    role = _role(request)
    if role != "customer":
        return render(request, "403.html", {"message": "Trang này chỉ dành cho khách hàng."}, status=403)

    customer_id = _entity_id(request)
    if customer_id is None:
        return redirect("login")

    error = None
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        quantity = int(request.POST.get("quantity", 1))
        r = _post(
            f"{SVC['cart']}/carts/{customer_id}/items/",
            json={"product_id": int(product_id), "quantity": quantity},
            request=request,
        )
        if r is not None and r.status_code == 201:
            _track_behavior_event(request, customer_id, int(product_id), "add_to_cart")
            return redirect("recommendations")
        error = _response_error(r, "cart-service unavailable")

    recommendations = _recommendation_products(request, customer_id, limit=12)
    return render(request, "recommendations.html", {
        "recommendations": recommendations,
        "customer_id": customer_id,
        "error": error,
    })


# ── Catalog ───────────────────────────────────────────────────────────────────

def catalog_view(request):
    allowed_tabs = {"categories", "brands", "product_types"}
    active_tab = request.GET.get("tab", "categories")
    if active_tab not in allowed_tabs:
        active_tab = "categories"

    endpoint_map = {
        "categories": "categories",
        "brands": "brands",
        "product_types": "product_types",
    }
    params = _list_query_params(request)
    payload = _get(f"{SVC['product']}/{endpoint_map[active_tab]}/", request, params=params)
    pagination = _pagination_context(payload, request, extra_query={"tab": active_tab})

    tab_labels = {
        "categories": "Danh mục",
        "brands": "Thương hiệu",
        "product_types": "Loại sản phẩm",
    }

    return render(request, "catalog.html", {
        "active_tab": active_tab,
        "active_label": tab_labels[active_tab],
        "items": _list_data(payload),
        "pagination": pagination,
    })


# ── AI Chatbot Proxy ──────────────────────────────────────────────────────────
import json as _json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

@csrf_exempt
@require_POST
def ai_chat_proxy(request):
    """
    Proxy endpoint: POST /ai/chat/
    Forwards request body to recommender-ai-service so the browser
    never needs to cross origins (no CORS issue).
    """
    try:
        body = _json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    recommender_url = f"{SVC['recommender']}/api/recommender/chat-ktmp"
    last_error = None
    for attempt in range(1, 4):
        try:
            # Cho request AI thời gian dài hơn vì lần đầu có thể load model.
            r = requests.post(recommender_url, json=body, timeout=90)
            return JsonResponse(r.json(), status=r.status_code)
        except requests.exceptions.Timeout as e:
            last_error = e
            logger.warning(f"[AI proxy] timeout attempt={attempt}: {e}")
        except requests.exceptions.ConnectionError as e:
            last_error = e
            logger.warning(f"[AI proxy] connection attempt={attempt}: {e}")
            # Retry ngắn để giảm lỗi lúc recommender vừa khởi động.
            time.sleep(1.0)
            continue
        except requests.exceptions.RequestException as e:
            logger.warning(f"[AI proxy] {e}")
            return JsonResponse({"error": f"AI service unavailable: {str(e)}"}, status=503)

    if isinstance(last_error, requests.exceptions.Timeout):
        return JsonResponse(
            {"error": "AI service timeout — model có thể đang tải. Vui lòng thử lại sau 10-20 giây."},
            status=504,
        )
    return JsonResponse({"error": f"AI service unavailable: {str(last_error)}"}, status=503)
