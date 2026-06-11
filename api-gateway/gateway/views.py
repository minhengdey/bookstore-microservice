from django.shortcuts import render, redirect
from django.conf import settings
import requests, logging, hmac, hashlib, time as _time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from urllib.parse import urlencode
from collections import defaultdict
from django.core.cache import cache
import os
from datetime import datetime

from .permissions import _role, _entity_id, require_roles, require_customer_or_staff, customer_can_only_own, require_auth

logger = logging.getLogger(__name__)
SVC = settings.SERVICE_URLS

# Internal service credentials
_INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN", "internal-dev-token")
_INTERNAL_SIGNING_SECRET = os.environ.get("INTERNAL_SIGNING_SECRET", "internal-signing-secret")
_SERVICE_NAME = os.environ.get("SERVICE_NAME", "api-gateway")

# ── Format helpers (dùng trong views, không cần custom template filter) ───────

ORDER_STATUS_VI = {
    # New statuses
    "DRAFT": "Bản nháp",
    "RESERVING_STOCK": "Đang giữ hàng",
    "STOCK_RESERVED": "Đã giữ hàng",
    "PAYMENT_PENDING": "Chờ thanh toán",
    "PAYMENT_PROCESSING": "Đang thanh toán",
    "WAITING_INVENTORY_CONFIRM": "Đã thanh toán",
    "COMPLETED": "Hoàn tất",
    "PAYMENT_FAILED": "Thanh toán thất bại",
    "CANCELLING": "Đang hủy",
    "CANCELLED": "Đã hủy",
    "REFUND_PENDING": "Chờ hoàn tiền",
    "REFUNDED": "Đã hoàn tiền",
    
    # Legacy statuses
    "pending_payment": "Chờ thanh toán",
    "pending":         "Chờ xử lý",
    "confirmed":       "Đã xác nhận",
    "processing":      "Đang xử lý",
    "shipped":         "Đang giao",
    "delivered":       "Đã giao",
    "cancelled":       "Đã hủy",
    "refunded":        "Đã hoàn tiền",
    "failed":          "Thất bại",
    "paid":            "Đã thanh toán",
    "failed_payment":  "Thanh toán thất bại",
    "RETURN_REQUESTED": "Yêu cầu trả hàng",
    "RETURNED":        "Đã nhận hoàn trả",
}

PRODUCT_STATUS_VI = {
    "active":        "Đang bán",
    "inactive":      "Ngừng bán",
    "out_of_stock":  "Hết hàng",
}


def _fmt_vnd(value):
    """1890000 → '1.890.000₫'"""
    try:
        amount = float(value)
        return f"{int(amount):,}".replace(",", ".") + "₫"
    except (TypeError, ValueError):
        return f"{value}₫" if value else "0₫"


def _fmt_date(value):
    """'2026-05-31T07:28:06.992173' → '31/05/2026 07:28'"""
    if not value:
        return "—"
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")
    s = str(value).strip()
    for fmt, length in (
        ("%Y-%m-%dT%H:%M:%S.%f", 26),
        ("%Y-%m-%dT%H:%M:%S",    19),
        ("%Y-%m-%d %H:%M:%S.%f", 26),
        ("%Y-%m-%d %H:%M:%S",    19),
        ("%Y-%m-%d",             10),
    ):
        try:
            dt = datetime.strptime(s[:length], fmt)
            return dt.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            continue
    return s


def _fmt_order(order):
    """Enrich một order dict với các field đã format."""
    if not isinstance(order, dict):
        return order
    status_raw = order.get("status", "")
    return {
        **order,
        "order_date_fmt":   _fmt_date(order.get("order_date")),
        "total_amount_fmt": _fmt_vnd(order.get("total_amount", 0)),
        "status_vi":        ORDER_STATUS_VI.get(status_raw, status_raw.replace("_", " ").title() if status_raw else "—"),
    }


def _fmt_product(p):
    """Enrich một product dict với price đã format."""
    if not isinstance(p, dict):
        return p
    status_raw = p.get("status", "active")
    return {
        **p,
        "price_fmt":  _fmt_vnd(p.get("price", 0)),
        "status_vi":  PRODUCT_STATUS_VI.get(status_raw, status_raw),
    }

# Simple request cache
_req_cache = {}
_req_cache_ttl = {}

# Global session to reuse HTTP connections and enable pooling
SESSION = requests.Session()
adapter = HTTPAdapter(pool_connections=50, pool_maxsize=50, max_retries=Retry(total=1, backoff_factor=0.1))
SESSION.mount("http://", adapter)
SESSION.mount("https://", adapter)


def _parallel_call(func_calls, max_workers=8):
    """Execute a list of (func, args, kwargs) in parallel.

    Returns list of results in the same order. Exceptions become None.
    """
    results = [None] * len(func_calls)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_to_index = {}
        for idx, (fn, args, kwargs) in enumerate(func_calls):
            future = ex.submit(fn, *args, **(kwargs or {}))
            future_to_index[future] = idx
        for fut in as_completed(future_to_index):
            idx = future_to_index[fut]
            try:
                results[idx] = fut.result()
            except Exception:
                results[idx] = None
    return results


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
    print(f"[DEBUG _auth_headers] Request payload is: {payload}")
    if not payload:
        return {}
    roles = payload.get("roles", [])
    headers = {
        "X-User-Id":   str(payload.get("user_id", "")),
        "X-Roles":     (",".join(roles) if isinstance(roles, list) else str(roles)).lower(),
        "X-User-Role": (",".join(roles) if isinstance(roles, list) else str(roles)).lower(),
        "X-Role":      (",".join(roles) if isinstance(roles, list) else str(roles)).lower(),
        "X-Entity-Id": str(payload.get("entity_id", "")),
        "X-Username":  str(payload.get("username", "")),
        "X-User-Status": str(payload.get("status", "ACTIVE")),
        "X-Role-Version": str(payload.get("role_version", 1)),
    }
    print(f"[DEBUG _auth_headers] Returning headers: {headers}")
    return headers


def _add_internal_headers(headers, body_str=""):
    timestamp = str(int(time.time()))
    signature = hmac.new(
        _INTERNAL_SIGNING_SECRET.encode("utf-8"),
        f"{timestamp}.{body_str}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    headers.update({
        "X-Internal-Token": _INTERNAL_TOKEN,
        "X-Service-Name": _SERVICE_NAME,
        "X-Timestamp": timestamp,
        "X-Signature": signature,
    })
    return headers

def _get(url, request=None, cache_ttl=0, **kwargs):
    """GET with optional caching. cache_ttl in seconds (0=no cache)."""
    # Check cache
    now = time.time()
    # Build cache key including params if present so different queries cache separately
    params = kwargs.get("params") or {}
    try:
        if params:
            # Sort params for stable key
            param_items = sorted(params.items())
            cache_key = url + "?" + urlencode(param_items)
        else:
            cache_key = url
    except Exception:
        cache_key = url
    if cache_ttl > 0:
        try:
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug(f"[CACHE HIT redis] {cache_key}")
                return cached
        except Exception:
            # Fallback to in-process cache if redis unavailable
            if cache_key in _req_cache and now < _req_cache_ttl.get(cache_key, 0):
                logger.debug(f"[CACHE HIT local] {cache_key}")
                return _req_cache[cache_key]
    
    try:
        headers = _auth_headers(request) if request else {}
        _add_internal_headers(headers, "")
        r = SESSION.get(url, headers=headers, timeout=60, **kwargs)
        result = r.json() if r.status_code == 200 else []
        
        # Cache if requested (prefer Redis via Django cache)
        if cache_ttl > 0:
            try:
                cache.set(cache_key, result, timeout=cache_ttl)
                logger.debug(f"[CACHE SET redis] {cache_key} for {cache_ttl}s")
            except Exception:
                _req_cache[cache_key] = result
                _req_cache_ttl[cache_key] = now + cache_ttl
                logger.debug(f"[CACHE SET local] {cache_key} for {cache_ttl}s")
        
        return result
    except requests.exceptions.RequestException as e:
        logger.warning(f"[GET] {url} → {e}")
        # Return cached value if available, even if expired
        if cache_key in _req_cache:
            logger.warning(f"[FALLBACK TO STALE CACHE] {cache_key}")
            return _req_cache[cache_key]
        return []


def _post(url, json=None, request=None, method="POST"):
    try:
        headers = _auth_headers(request) if request else {}
        headers["Content-Type"] = "application/json"
        import json as _json
        body_str = _json.dumps(json, separators=(",", ":"), sort_keys=True) if json else ""
        _add_internal_headers(headers, body_str)
        
        # We must send data=body_str.encode('utf-8') instead of json=json
        # because requests.post(json=...) re-serializes with different spacing, breaking the signature.
        if method.upper() == "PUT":
            return SESSION.put(url, data=body_str.encode("utf-8"), headers=headers, timeout=5)
        elif method.upper() == "PATCH":
            return SESSION.patch(url, data=body_str.encode("utf-8"), headers=headers, timeout=5)
        return SESSION.post(url, data=body_str.encode("utf-8"), headers=headers, timeout=5)
    except requests.exceptions.RequestException as e:
        logger.warning(f"[{method.upper()}] {url} → {e}")
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
        _add_internal_headers(headers, "")
        return SESSION.delete(url, headers=headers, timeout=5)
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
    payload = _get(f"{SVC['product']}/{endpoint}/", request, params={"page_size": 200}, cache_ttl=300)
    items = _list_data(payload)
    result = {}
    for item in items:
        item_id = item.get("id")
        label = item.get(field_name)
        if item_id is not None and label:
            result[int(item_id)] = label
    return result


def _hydrate_book_catalog_data(request, product):
    calls = [
        (_catalog_name_map, (request, "authors", "author_name"), {}),
        (_catalog_name_map, (request, "genres", "genre_name"), {}),
        (_catalog_name_map, (request, "publishers", "publisher_name"), {}),
        (_catalog_name_map, (request, "categories", "category_name"), {}),
    ]
    author_map, genre_map, publisher_map, category_map = _parallel_call(calls, max_workers=4)
    return {
        "authors": [author_map.get(int(i), f"Author #{i}") for i in product.get("author_ids", [])],
        "genres": [genre_map.get(int(i), f"Genre #{i}") for i in product.get("genre_ids", [])],
        "publishers": [publisher_map.get(int(i), f"Publisher #{i}") for i in product.get("publisher_ids", [])],
        "categories": [category_map.get(int(i), f"Category #{i}") for i in product.get("category_ids", [])],
    }


def _recommendation_products(request, customer_id, limit=6):
    payload = _get(f"{SVC['recommender']}/recommendations/{customer_id}/", request, params={"limit": limit}, cache_ttl=5)
    if not isinstance(payload, dict):
        return []
    ids = payload.get("recommended_product_ids") or payload.get("recommended_product_ids") or []
    products = []
    # Fetch product details in parallel
    calls = [(_get, (f"{SVC['product']}/products/{pid}/", request), {"cache_ttl": 30}) for pid in ids]
    results = _parallel_call(calls, max_workers=min(8, len(calls) or 1))
    for data in results:
        if isinstance(data, dict) and data.get("id"):
            products.append(data)
    return products


# ── Auth ─────────────────────────────────────────────────────────────────────

_LOGIN_ROLES = {"customer", "staff", "admin"}


def _login_role(request) -> str:
    role = (request.POST.get("login_type") or request.GET.get("login_type") or "customer").strip().lower()
    return role if role in _LOGIN_ROLES else "customer"

def login_view(request):
    """Unified login page – customers and staff/managers."""
    login_type = _login_role(request)
    if request.method == "GET":
        return render(request, "login.html", {"login_type": login_type})

    username    = request.POST.get("username", "").strip()
    password    = request.POST.get("password", "")
    error = None

    url = f"{SVC['auth']}/auth/login/"

    try:
        r = requests.post(
            url,
            json={"username": username, "password": password, "role": login_type},
            timeout=5,
        )
        if r.status_code == 200:
            data = r.json()
            request.session["access_token"]  = data["access"]
            request.session["refresh_token"] = data["refresh"]
            request.session["user"]          = data["user"]
            roles = data["user"].get("roles", [])
            if any(r in roles for r in ("ADMIN", "SUPER_ADMIN", "MANAGER")):
                return redirect("admin_dashboard")
            if "STAFF" in roles:
                return redirect("staff_dashboard")
            return redirect("home")
        error = r.json().get("error", "Login failed")
    except requests.exceptions.RequestException:
        error = "Auth service unavailable"

    return render(request, "login.html", {"error": error, "login_type": login_type})


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
    calls = [
        (_get, (f"{SVC['product']}/products/", request), {"cache_ttl": 10}),
    ]
    # For staff we also fetch orders; do that in parallel when needed
    if role in ("staff", "manager"):
        calls.append((_get, (f"{SVC['order']}/orders/", request), {"cache_ttl": 10}))
    results = _parallel_call(calls, max_workers=len(calls))
    products_payload = results[0]
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
            "recommendations": [_fmt_product(r) for r in recommendations],
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
    orders_payload = results[1] if len(results) > 1 else _get(f"{SVC['order']}/orders/", request, cache_ttl=10)
    return render(request, "home.html", {
        "total_products": total_products,
        "total_customers": 0,
        "total_orders": _total_count(orders_payload),
        "user": user,
        "is_customer": False,
    })


# ── Products ─────────────────────────────────────────────────────────────────────

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
            "image_url": request.POST.get("image_url", "").strip(),
        }
        r = _post(f"{SVC['product']}/products/", json=payload, request=request)
        if r is not None and r.status_code == 201:
            return redirect("product_list")
        error = _response_error(r, "product-service unavailable")
    # Fetch products and categories in parallel to reduce latency
    params = _list_query_params(request)
    if request.GET.get("min_price"):
        params["min_price"] = request.GET.get("min_price")
    if request.GET.get("max_price"):
        params["max_price"] = request.GET.get("max_price")
    if request.GET.get("sort_by"):
        params["sort_by"] = request.GET.get("sort_by")
    if request.GET.get("category_id"):
        params["category_id"] = request.GET.get("category_id")

    calls = [
        (_get, (f"{SVC['product']}/products/", request), {"params": params, "cache_ttl": 10}),
        (_get, (f"{SVC['product']}/categories/", request), {"params": {"page_size": 100}, "cache_ttl": 300}),
    ]
    products_payload, categories_payload = _parallel_call(calls, max_workers=2)
    products_pagination = _pagination_context(products_payload, request)
    categories = _list_data(categories_payload)
    search_query = request.GET.get("search", "").strip()
    if role == "customer" and search_query:
        customer_id = _entity_id(request)
        for product in _list_data(products_payload)[:5]:
            product_id = product.get("id") if isinstance(product, dict) else None
            if product_id is not None:
                _track_behavior_event(request, customer_id, product_id, "search")
    return render(request, "products.html", {
        "products": [_fmt_product(p) for p in _list_data(products_payload)],
        "products_pagination": products_pagination,
        "categories": categories,
        "search_query": search_query,
        "category_id": request.GET.get("category_id", ""),
        "min_price": request.GET.get("min_price", ""),
        "max_price": request.GET.get("max_price", ""),
        "sort_by": request.GET.get("sort_by", "id"),
        "error": error,
        "can_manage_products": role in ("staff", "manager"),
    })


def promotion_list(request):
    payload = _get(f"{SVC['promotion']}/api/promotions/flash-sales/", request, params={"active": "true"}, cache_ttl=10)
    flash_sales = _list_data(payload)
    
    voucher_payload = _get(f"{SVC['promotion']}/api/promotions/vouchers/", request, params={"active": "true"}, cache_ttl=10)
    vouchers = _list_data(voucher_payload)
    
    return render(request, "promotions.html", {
        "flash_sales": flash_sales,
        "vouchers": vouchers,
        "user": request.session.get("user", {})
    })



def product_detail(request, product_id):
    role = _role(request)
    customer_id = _entity_id(request) if role == "customer" else None
    product = _get(f"{SVC['product']}/products/{product_id}/", request, cache_ttl=30)
    if not isinstance(product, dict) or not product.get("id"):
        return render(request, "403.html", {"message": "Không tìm thấy sản phẩm."}, status=404)

    error = None
    if request.method == "POST":
        if customer_id is None:
            return redirect("login")
        quantity = int(request.POST.get("quantity", 1))
        payload = {"product_id": int(product_id), "quantity": quantity, "unit_price": float(product.get("price") or 0)}
        if request.POST.get("variant_id"):
            payload["variant_id"] = int(request.POST.get("variant_id"))
            
        r = _post(
            f"{SVC['cart']}/carts/{customer_id}/items/",
            json=payload,
            request=request,
        )
        if r is not None and r.status_code == 201:
            _track_behavior_event(request, customer_id, product_id, "add_to_cart")
            return redirect("view_cart", customer_id=customer_id)
        error = _response_error(r, "cart-service unavailable")

    if customer_id is not None:
        _track_behavior_event(request, customer_id, product_id, "click")
        _track_behavior_event(request, customer_id, product_id, "view")

    raw_recommendations = _recommendation_products(request, customer_id, limit=7) if customer_id else []
    recommendations = [r for r in raw_recommendations if str(r.get("id")) != str(product_id)][:6]
    
    reviews_payload = _get(f"{SVC['interaction_api']}/reviews/", request, params={"product_id": product_id}, cache_ttl=5)
    reviews = _list_data(reviews_payload)
    
    in_wishlist = False
    if customer_id:
        wishlist_payload = _get(f"{SVC['interaction_api']}/wishlists/", request, params={"customer_id": customer_id, "product_id": product_id}, cache_ttl=0)
        in_wishlist = len(_list_data(wishlist_payload)) > 0
    
    return render(request, "product_detail.html", {
        "product": _fmt_product(product),
        "recommendations": [_fmt_product(r) for r in recommendations],
        "reviews": reviews,
        "in_wishlist": in_wishlist,
        "is_customer": role == "customer",
        "customer_id": customer_id,
        "error": error,
    })

@require_roles("customer")
def product_review(request, product_id):
    if request.method == "POST":
        customer_id = _entity_id(request)
        rating = int(request.POST.get("rating", 5))
        comment_text = request.POST.get("comment_text", "")
        
        # Check verified purchase
        orders = _list_data(_get(f"{SVC['order']}/orders/", request, cache_ttl=0))
        verified = False
        for order in orders:
            status = str(order.get("status")).upper()
            if status in ("COMPLETED", "DELIVERED", "WAITING_INVENTORY_CONFIRM", "PAID"):
                for item in order.get("items", []):
                    if str(item.get("product_id")) == str(product_id):
                        verified = True
                        break
            if verified: break
            
        if not verified:
            return render(request, "403.html", {"message": "Bạn chỉ có thể đánh giá sản phẩm sau khi đã mua hàng thành công."}, status=403)
            
        payload = {
            "product_id": int(product_id),
            "customer_id": int(customer_id),
            "rating": rating,
            "comment_text": comment_text,
            "verified_purchase": True,
            "image_urls": []
        }
        _post(f"{SVC['interaction_api']}/reviews/", json=payload, request=request)
        
    return redirect("product_detail", product_id=product_id)

@require_roles("customer")
def product_wishlist_toggle(request, product_id):
    if request.method == "POST":
        customer_id = _entity_id(request)
        wishlist_payload = _get(f"{SVC['interaction_api']}/wishlists/", request, params={"customer_id": customer_id, "product_id": product_id}, cache_ttl=0)
        items = _list_data(wishlist_payload)
        
        if items:
            _delete(f"{SVC['interaction_api']}/wishlists/{items[0]['id']}/", request)
        else:
            _post(f"{SVC['interaction_api']}/wishlists/", json={"customer_id": customer_id, "product_id": product_id}, request=request)
            
    return redirect(request.META.get('HTTP_REFERER', f"/products/{product_id}/"))

@require_roles("customer")
def wishlist_view(request):
    customer_id = _entity_id(request)
    wishlist_payload = _get(f"{SVC['interaction_api']}/wishlists/", request, params={"customer_id": customer_id}, cache_ttl=0)
    wishlist_items = _list_data(wishlist_payload)
    
    products = []
    if wishlist_items:
        calls = [(_get, (f"{SVC['product']}/products/{w['product_id']}/", request), {"cache_ttl": 30}) for w in wishlist_items]
        results = _parallel_call(calls, max_workers=8)
        products = [_fmt_product(r) for r in results if isinstance(r, dict) and r.get("id")]
        
    return render(request, "wishlist.html", {"products": products})

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
        product_id = request.POST.get("product_id") or request.POST.get("product_id")
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
                "products": _list_data(_get(f"{SVC['product']}/products/", request, params={"page_size": 500}, cache_ttl=10)),
                "error": "Vui lòng chọn sản phẩm.",
            })
        product_price = 0
        products_list = _list_data(_get(f"{SVC['product']}/products/", request, params={"page_size": 500}, cache_ttl=10))
        for p in products_list:
            if str(p.get("id")) == str(product_id):
                product_price = float(p.get("price") or 0)
                break
                
        payload = {"product_id": int(product_id), "quantity": quantity, "unit_price": product_price}
        if request.POST.get("variant_id"):
            payload["variant_id"] = int(request.POST.get("variant_id"))
            
        r = _post(
            f"{SVC['cart']}/carts/{customer_id}/items/",
            json=payload,
            request=request,
        )
        if r is not None and r.status_code == 201:
            if _role(request) == "customer":
                _track_behavior_event(request, customer_id, int(product_id), "add_to_cart")
            return redirect("view_cart", customer_id=customer_id)
        error = _response_error(r, "cart-service unavailable")

    # Fetch cart and product list in parallel
    calls = [
        (_get, (f"{SVC['cart']}/carts/{customer_id}/", request), {}),
        (_get, (f"{SVC['product']}/products/", request), {"params": {"page_size": 500}, "cache_ttl": 10}),
    ]
    cart, products_payload = _parallel_call(calls, max_workers=2)
    product_map = {b.get("id"): b for b in _list_data(products_payload) if isinstance(b, dict) and b.get("id") is not None}

    cart_items = []
    for item in (cart or {}).get("items", []):
        bid = item.get("product_id", item.get("product_id"))
        product = product_map.get(bid, {})
        unit_price = float(item.get("unit_price") or 0)
        qty = int(item.get("quantity") or 0)
        
        variant_str = ""
        if item.get("variant_id"):
            for v in product.get("variants", []):
                if v.get("id") == item["variant_id"]:
                    variant_str = f" ({v.get('color')} - {v.get('size')})"
                    break
                    
        cart_items.append({
            **item,
            "product_name": (product.get("name") or f"Sản phẩm #{bid}") + variant_str,
            "line_total": unit_price * qty,
        })

    if isinstance(cart, dict):
        cart["items"] = cart_items

    return render(request, "cart.html", {
        "cart": cart, "customer_id": customer_id, "products": _list_data(products_payload), "error": error,
    })


# ── Shipping helpers ───────────────────────────────────────────────────────────

_CITY_DISTANCE_KM = {
    "hà nội": 5, "ha noi": 5, "hanoi": 5,
    "hồ chí minh": 15, "ho chi minh": 15, "hcm": 15, "tp.hcm": 15,
    "đà nẵng": 25, "da nang": 25,
    "cần thơ": 35, "can tho": 35,
    "hải phòng": 20, "hai phong": 20,
}


def _estimate_distance_km(city):
    if not city:
        return 10.0
    return float(_CITY_DISTANCE_KM.get(str(city).strip().lower(), 15.0))


def _cart_weight(items):
    return sum(max(1, int(it.get("quantity", 1))) * 0.5 for it in items)


def _fetch_shipping_fee(request, method_id, items, city=None):
    payload = {
        "shipping_method_id": int(method_id),
        "total_weight": _cart_weight(items),
        "distance_km": _estimate_distance_km(city),
    }
    resp = _post(f"{SVC['ship']}/api/shipping/calculate-fee/", json=payload, request=request)
    if resp and resp.status_code == 200:
        return resp.json()
    return {"shipping_fee": 30000}


def _enrich_shipping_methods(request, methods, items, city=None):
    enriched = []
    for method in methods:
        fee_data = _fetch_shipping_fee(request, method["id"], items, city) if method.get("id") else {}
        enriched.append({**method, "calculated_fee": fee_data.get("shipping_fee", method.get("rate", 0))})
    return enriched


def _hydrate_cart_items_with_products(items, product_map):
    hydrated = []
    for it in items:
        pid = it.get("product_id")
        prod = product_map.get(pid, {})
        variant_str = ""
        variant_name = ""
        if it.get("variant_id"):
            for v in prod.get("variants", []):
                if v.get("id") == it["variant_id"]:
                    variant_name = f"{v.get('color')} - {v.get('size')}"
                    variant_str = f" ({variant_name})"
                    break
        prod_name = prod.get("name") or f"Sản phẩm #{pid}"
        hydrated.append({
            **it,
            "product_name": prod_name + variant_str,
            "variant_name": variant_name,
        })
    return hydrated


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

    auth_user_id = request.session.get("user", {}).get("id")

    if request.method == "POST":
        address_id = request.POST.get("address_id")
        promotion_code = request.POST.get("promotion_code", "").strip()
        user_notes = request.POST.get("notes", "").strip()
        shipping_method_id = request.POST.get("shipping_method_id")

        address_snapshot = None
        city = None
        if address_id and auth_user_id:
            addr = _get(f"{SVC['user']}/internal/users/{auth_user_id}/addresses/", request)
            for a in _list_data(addr) if isinstance(addr, list) else ([addr] if isinstance(addr, dict) else []):
                if str(a.get("id")) == str(address_id):
                    address_snapshot = a
                    city = a.get("city")
                    break

        shipping_fee = 30000
        if shipping_method_id:
            fee_data = _fetch_shipping_fee(request, shipping_method_id, items, city)
            shipping_fee = fee_data.get("shipping_fee", 30000)

        products_payload = _get(f"{SVC['product']}/products/", request, params={"page_size": 500}, cache_ttl=10)
        product_map = {b.get("id"): b for b in _list_data(products_payload) if isinstance(b, dict) and b.get("id") is not None}
        order_items = _hydrate_cart_items_with_products(items, product_map)

        payload = {
            "customer_id": customer_id,
            "items": [
                {
                    "product_id": it["product_id"],
                    "variant_id": it.get("variant_id"),
                    "product_name": it.get("product_name"),
                    "variant_name": it.get("variant_name"),
                    "quantity": it["quantity"],
                    "unit_price": float(it.get("unit_price", 0))
                } for it in order_items
            ],
            "shipping_fee": shipping_fee,
            "shipping_method_id": int(shipping_method_id) if shipping_method_id else None,
            "address_id": address_id,
            "shipping_address": address_snapshot,
            "promotion_code": promotion_code,
            "notes": user_notes
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

    products_payload = _get(f"{SVC['product']}/products/", request, params={"page_size": 500}, cache_ttl=10)
    product_map = {b.get("id"): b for b in _list_data(products_payload) if isinstance(b, dict) and b.get("id") is not None}
    hydrated_items = _hydrate_cart_items_with_products(items, product_map)

    addresses = _list_data(_get(f"{SVC['user']}/internal/users/{auth_user_id}/addresses/", request)) if auth_user_id else []
    default_city = next((a.get("city") for a in addresses if a.get("is_default")), None)
    if not default_city and addresses:
        default_city = addresses[0].get("city")
    shipping_methods = _enrich_shipping_methods(
        request,
        _list_data(_get(f"{SVC['ship']}/api/methods/", request)),
        hydrated_items,
        default_city,
    )
    subtotal = float(cart.get("total_price", 0) or 0)

    return render(request, "checkout.html", {
        "customer_id": customer_id, "cart": cart, "cart_items": hydrated_items,
        "addresses": addresses,
        "shipping_methods": shipping_methods,
        "subtotal": subtotal,
    })

# ── Thanh toán đơn hàng ────────────────────────────────────────────────────────

@require_customer_or_staff
def order_pay(request, order_id):
    """GET: form chọn phương thức thanh toán. POST: gửi thanh toán."""
    order = _get(f"{SVC['order']}/orders/{order_id}/", request)
    if not order or not isinstance(order, dict):
        return render(request, "403.html", {"message": "Không tìm thấy đơn hàng."}, status=404)

    methods_payload = _list_data(_get(f"{SVC['pay']}/payment-methods/", request))
    if not methods_payload:
        methods_payload = [
            {"id": 1, "method_name": "Thanh toán khi nhận hàng (COD)"},
            {"id": 2, "method_name": "VNPay (Mock)"},
            {"id": 3, "method_name": "MoMo (Mock)"},
            {"id": 4, "method_name": "ZaloPay (Mock)"},
        ]

    if request.method == "POST":
        method_id = request.POST.get("payment_method_id")
        amount = request.POST.get("payment_amount", "").strip() or str(order.get("total_amount", 0))
        if not method_id:
            return render(request, "order_pay.html", {
                "order": order, "order_id": order_id, "payment_methods": methods_payload,
                "error": "Vui lòng chọn phương thức thanh toán.",
            })
            
        try:
            amount_float = float(amount)
        except ValueError:
            amount_float = float(order.get("total_amount", 0))
            
        # Instead of calling payment directly and assuming SUCCESS, we simulate redirect to Payment Gateway
        method_name = next((m.get("method_name") for m in methods_payload if str(m.get("id")) == method_id), "VNPay (Mock)")
        if "COD" in method_name:
            # COD is successfully recorded right away as PENDING payment
            r = _post(
                f"{SVC['pay']}/payments/",
                json={
                    "order_id": order_id,
                    "payment_amount": amount_float,
                    "payment_method_id": int(method_id),
                },
                request=request,
            )
            request.session["order_success"] = f"Đã đặt hàng #{order_id} thành công với hình thức COD."
            return redirect("order_list")
        else:
            # Simulate Redirect to Payment Gateway (Mock)
            return render(request, "payment_gateway_mock.html", {
                "order": order,
                "amount": amount_float,
                "method_id": method_id,
                "method_name": method_name
            })

    return render(request, "order_pay.html", {
        "order": order, "order_id": order_id, "payment_methods": methods_payload,
    })

@require_customer_or_staff
def payment_callback(request, order_id):
    """Callback returned from VNPay/MoMo."""
    status = request.GET.get("status", "SUCCESS") # SUCCESS, FAILED, CANCELLED
    method_id = request.GET.get("method_id")
    amount = request.GET.get("amount")
    
    if status == "SUCCESS":
        r = _post(
            f"{SVC['pay']}/payments/",
            json={
                "order_id": order_id,
                "payment_amount": float(amount) if amount else 0,
                "payment_method_id": int(method_id) if method_id else None,
            },
            request=request,
        )
        # Update payment status via payment-service if it has such API, 
        # or it will trigger outbox to update order to PAID.
        request.session["order_success"] = f"Thanh toán đơn #{order_id} thành công!"
    elif status == "CANCELLED":
        request.session["order_success"] = f"Bạn đã hủy thanh toán đơn #{order_id}."
    else:
        request.session["order_success"] = f"Thanh toán đơn #{order_id} thất bại!"
        
    return redirect("order_list")


# ── Orders ────────────────────────────────────────────────────────────────────

def _enrich_orders_with_customer_name(request, orders):
    """Fetch username cho từng customer_id trong danh sách đơn hàng (batch, parallel)."""
    if not orders:
        return orders
    # Lấy tập hợp customer_id duy nhất
    customer_ids = list({o.get("customer_id") for o in orders if o.get("customer_id") is not None})
    if not customer_ids:
        return orders
    calls = [
        (_get, (f"{SVC['user']}/internal/users/{cid}/",), {"cache_ttl": 60})
        for cid in customer_ids
    ]
    results = _parallel_call(calls, max_workers=min(8, len(calls)))
    id_to_name = {}
    for cid, data in zip(customer_ids, results):
        if isinstance(data, dict) and data.get("username"):
            id_to_name[cid] = data["username"]
    # Gắn customer_name vào mỗi order
    enriched = []
    for order in orders:
        cid = order.get("customer_id")
        enriched.append({**order, "customer_name": id_to_name.get(cid)})
    return enriched

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
    orders = _list_data(orders_payload)
    orders = _enrich_orders_with_customer_name(request, orders)
    return render(request, "orders.html", {
        "orders": orders,
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
    orders = _list_data(orders_payload)
    orders = _enrich_orders_with_customer_name(request, orders)
    customer_name = orders[0].get("customer_name") if orders else None
    response = render(request, "orders.html", {
        "orders": orders,
        "orders_pagination": _pagination_context(orders_payload, request),
        "customer_id": customer_id,
        "customer_name": customer_name,
        "order_success_msg": success_msg,
    })
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


@require_customer_or_staff
def order_tracking(request, order_id):
    order = _get(f"{SVC['order']}/orders/{order_id}/", request)
    if not order or not isinstance(order, dict):
        return render(request, "403.html", {"message": "Không tìm thấy đơn hàng."}, status=404)
        
    shipping = _get(f"{SVC['ship']}/api/shippings/order/{order_id}/", request)
    if not shipping or (isinstance(shipping, dict) and shipping.get("error")):
        shipping = _get(f"{SVC['ship']}/shippings/order/{order_id}/", request)
    return render(request, "tracking.html", {
        "order": order,
        "shipping": shipping if isinstance(shipping, dict) and "error" not in shipping else None
    })


# ── Returns (Trả hàng) ────────────────────────────────────────────────────────

@require_auth
def returns_list(request):
    customer_id = _entity_id(request)
    orders = _list_data(_get(f"{SVC['order']}/orders/?customer_id={customer_id}", request))
    success_msg = request.session.pop("return_success", None)
    error_msg = request.session.pop("return_error", None)
    response = render(request, "returns.html", {
        "orders": [_fmt_order(o) for o in orders],
        "return_success": success_msg,
        "return_error": error_msg,
    })
    return response


@require_auth
def return_request(request, order_id):
    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        resp = _post(f"{SVC['order']}/orders/{order_id}/return/", json={"reason": reason}, request=request)
        if resp and resp.status_code == 200:
            request.session["return_success"] = f"Đã gửi yêu cầu trả hàng cho đơn #{order_id}."
        else:
            err = _response_error(resp, "Không thể gửi yêu cầu trả hàng")
            request.session["return_error"] = err.get("error") if isinstance(err, dict) else str(err)
    return redirect("returns_list")

def order_status_api(request):
    """API endpoint for AJAX polling of order statuses."""
    eid = _entity_id(request)
    if not eid:
        from django.http import JsonResponse
        return JsonResponse({"error": "Unauthorized"}, status=401)
        
    ids_param = request.GET.get("ids", "")
    if not ids_param:
        from django.http import JsonResponse
        return JsonResponse({"statuses": {}})
        
    try:
        ids = [int(x.strip()) for x in ids_param.split(",") if x.strip().isdigit()]
    except ValueError:
        ids = []
        
    if not ids:
        from django.http import JsonResponse
        return JsonResponse({"statuses": {}})
        
    orders_payload = _get(f"{SVC['order']}/orders/", request, params={"customer_id": eid})
    orders = _list_data(orders_payload)
    
    statuses = {}
    from gateway.templatetags.custom_filters import vi_status
    for o in orders:
        oid = o.get("id")
        if oid in ids:
            status_raw = o.get("status")
            badge = "badge-warning"
            if status_raw in ('paid', 'COMPLETED', 'WAITING_INVENTORY_CONFIRM'):
                badge = "badge-info"
            elif status_raw == "delivered":
                badge = "badge-success"
            elif status_raw in ("cancelled", "failed_payment"):
                badge = "badge-danger"
                
            statuses[str(oid)] = {
                "raw": status_raw,
                "vi": vi_status(status_raw),
                "badge": badge
            }
            
    from django.http import JsonResponse
    return JsonResponse({"statuses": statuses})


@require_customer_or_staff
def order_detail(request, order_id):
    order = _get(f"{SVC['order']}/orders/{order_id}/", request)
    if not order or not isinstance(order, dict):
        return render(request, "403.html", {"message": "Không tìm thấy đơn hàng."}, status=404)
        
    # Get product details for items
    products_payload = _get(f"{SVC['product']}/products/", request, params={"page_size": 500}, cache_ttl=10)
    product_map = {p.get("id"): p for p in _list_data(products_payload) if isinstance(p, dict) and p.get("id")}
    
    items = order.get("items", [])
    hydrated_items = []
    for it in items:
        pid = it.get("product_id")
        prod = product_map.get(pid, {})
        hydrated_items.append({
            **it,
            "product_name": prod.get("name") or f"Sản phẩm #{pid}",
            "unit_price_fmt": _fmt_vnd(it.get("unit_price", 0)),
            "line_total_fmt": _fmt_vnd(float(it.get("unit_price", 0)) * int(it.get("quantity", 0))),
        })
    order["items"] = hydrated_items
    
    # Enrich with customer name if needed
    order = _enrich_orders_with_customer_name(request, [order])[0]
    
    return render(request, "order_detail.html", {
        "order": _fmt_order(order),
        "is_customer": _role(request) == "customer",
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
    payload = _get(f"{SVC['product']}/{endpoint_map[active_tab]}/", request, params=params, cache_ttl=300)
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

# ── Profile & Addresses ──────────────────────────────────────────────────────

@require_auth
def profile_view(request):
    user_id = request.session.get("user", {}).get("id")
    profile = _get(f"{SVC['user']}/internal/users/{user_id}/", request)
    addresses = _list_data(_get(f"{SVC['user']}/internal/users/{user_id}/addresses/", request))
    
    return render(request, "profile.html", {
        "profile": profile,
        "addresses": addresses
    })

@require_auth
def address_add(request):
    if request.method == "POST":
        user_id = request.session.get("user", {}).get("id")
        payload = {
            "recipient_name": request.POST.get("recipient_name"),
            "phone": request.POST.get("phone"),
            "address_line": request.POST.get("address_line"),
            "city": request.POST.get("city"),
            "state": request.POST.get("state", ""),
            "country": request.POST.get("country", "VN"),
            "postal_code": request.POST.get("postal_code", "000000"),
            "is_default": request.POST.get("is_default") == "on"
        }
        _post(f"{SVC['user']}/internal/users/{user_id}/addresses/", json=payload, request=request)
    return redirect("profile")

@require_auth
def address_delete(request, address_id):
    if request.method == "POST":
        user_id = request.session.get("user", {}).get("id")
        _delete(f"{SVC['user']}/internal/users/{user_id}/addresses/{address_id}/", request)
    return redirect("profile")

@require_auth
def address_set_default(request, address_id):
    if request.method == "POST":
        user_id = request.session.get("user", {}).get("id")
        _post(f"{SVC['user']}/internal/users/{user_id}/addresses/{address_id}/", json={"is_default": True}, request=request, method="PUT")
    return redirect("profile")

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
            r = SESSION.post(recommender_url, json=body, timeout=90)
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


# ── Customer Support (Tickets) ────────────────────────────────────────────────

@require_auth
def support_list(request):
    customer_id = _entity_id(request)
    tickets = _list_data(_get(f"{SVC['interaction_api']}/tickets/", request, params={"customer_id": customer_id}))
    return render(request, "support/list.html", {"tickets": tickets})


@require_auth
def support_create(request):
    customer_id = _entity_id(request)
    if request.method == "POST":
        payload = {
            "customer_id": customer_id,
            "subject": request.POST.get("subject", "").strip(),
            "content": request.POST.get("content", "").strip(),
            "order_id": int(request.POST.get("order_id")) if request.POST.get("order_id") else None,
        }
        resp = _post(f"{SVC['interaction_api']}/tickets/", json=payload, request=request)
        if resp and resp.status_code in (200, 201):
            ticket = resp.json()
            return redirect("support_detail", ticket_id=ticket.get("id"))
    orders = _list_data(_get(f"{SVC['order']}/orders/?customer_id={customer_id}", request))
    return render(request, "support/create.html", {"orders": orders})


@require_auth
def support_detail(request, ticket_id):
    customer_id = _entity_id(request)
    ticket = _get(f"{SVC['interaction_api']}/tickets/{ticket_id}/", request)
    if not ticket or ticket.get("customer_id") != customer_id:
        return render(request, "403.html", {"message": "Bạn không có quyền xem ticket này."}, status=403)

    if request.method == "POST":
        reply_message = request.POST.get("message", "").strip()
        if reply_message:
            _post(f"{SVC['interaction_api']}/ticket-replies/", json={
                "ticket": ticket_id,
                "sender_id": customer_id,
                "is_staff": False,
                "message": reply_message,
            }, request=request)
        return redirect("support_detail", ticket_id=ticket_id)

    return render(request, "support/detail.html", {"ticket": ticket})
