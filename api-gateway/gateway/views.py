from django.shortcuts import render, redirect
from django.conf import settings
import requests, logging, hmac, hashlib, time as _time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from collections import defaultdict
from django.core.cache import cache
import os
from datetime import datetime

from .permissions import _role, _entity_id, _user, require_roles, require_customer_or_staff, customer_can_only_own, require_auth
from .behavior_tracking import track_behavior, track_order_purchases

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
    "PENDING_PAYMENT": "Chờ thanh toán",
    "PAID":            "Đã thanh toán",
    "PROCESSING":      "Đang xử lý",
    "SHIPPING":        "Đang giao",
    "DELIVERED":       "Đã giao",
    "CANCELLED":       "Đã hủy",
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

# Chỉ cho đánh giá khi đơn đã giao thành công
_REVIEW_ELIGIBLE_ORDER_STATUSES = frozenset({
    "DELIVERED", "COMPLETED",
})
_CANCELLED_ORDER_STATUSES = frozenset({
    "CANCELLED", "REFUNDED", "RETURNED", "PAYMENT_FAILED",
    "FAILED_PAYMENT", "CANCELLING",
})

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
    snapshot = order.get("shipping_address_snapshot") or {}
    items = order.get("items") or []
    subtotal = sum(
        float(it.get("unit_price") or 0) * int(it.get("quantity") or 0)
        for it in items
    )
    addr_parts = [
        snapshot.get("address_line"),
        snapshot.get("city"),
        snapshot.get("state"),
    ]
    recipient_address = ", ".join(p for p in addr_parts if p)
    return {
        **order,
        "order_date_fmt":   _fmt_date(order.get("order_date")),
        "total_amount_fmt": _fmt_vnd(order.get("total_amount", 0)),
        "subtotal_fmt":     _fmt_vnd(subtotal),
        "shipping_fee_fmt": _fmt_vnd(order.get("shipping_fee", 0)),
        "discount_amount_fmt": _fmt_vnd(order.get("discount_amount", 0)),
        "status_vi":        ORDER_STATUS_VI.get(status_raw, status_raw.replace("_", " ").title() if status_raw else "—"),
        "shipping_address": snapshot,
        "recipient_name":   snapshot.get("recipient_name") or "",
        "recipient_phone":  snapshot.get("phone") or "",
        "recipient_address": recipient_address,
        "shipping_method_name": snapshot.get("shipping_method_name") or "",
        "notes":            (order.get("notes") or "").strip(),
    }


def _product_list_price(p):
    return float(p.get("price") or 0)


def _product_effective_price(p):
    if p.get("is_flash_sale") and p.get("flash_sale_price") is not None:
        return float(p.get("flash_sale_price") or 0)
    return float(p.get("effective_price") or p.get("price") or 0)


def _fmt_product(p):
    """Enrich một product dict với price đã format."""
    if not isinstance(p, dict):
        return p
    status_raw = p.get("status", "active")
    list_price = _product_list_price(p)
    effective = _product_effective_price(p)
    on_flash_sale = bool(p.get("is_flash_sale")) and effective < list_price
    discount_pct = round((1 - effective / list_price) * 100) if on_flash_sale and list_price else 0
    return {
        **p,
        "list_price": list_price,
        "effective_price": effective,
        "display_price": effective,
        "display_price_fmt": _fmt_vnd(effective),
        "price_fmt": _fmt_vnd(list_price),
        "list_price_fmt": _fmt_vnd(list_price),
        "original_price_fmt": _fmt_vnd(list_price),
        "flash_sale_price_fmt": _fmt_vnd(effective) if on_flash_sale else None,
        "is_flash_sale_active": on_flash_sale,
        "discount_pct": discount_pct,
        "status_vi": PRODUCT_STATUS_VI.get(status_raw, status_raw),
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


def _customer_orders(request, page_size=200):
    """Lấy toàn bộ đơn hàng của khách (gộp các trang phân trang)."""
    first = _get(
        f"{SVC['order']}/orders/",
        request,
        params={"page_size": page_size},
        cache_ttl=0,
    )
    if not isinstance(first, dict):
        return _list_data(first)
    orders = list(first.get("results") or [])
    total_pages = first.get("total_pages", 1) or 1
    for page in range(2, int(total_pages) + 1):
        payload = _get(
            f"{SVC['order']}/orders/",
            request,
            params={"page": page, "page_size": page_size},
            cache_ttl=0,
        )
        orders.extend(_list_data(payload))
    return orders


def _customer_product_review_state(request, product_id):
    """Trả về: delivered | awaiting_delivery | none."""
    product_key = str(product_id)
    awaiting = False
    for order in _customer_orders(request):
        status = str(order.get("status", "")).upper()
        has_product = any(
            str(item.get("product_id")) == product_key
            for item in order.get("items") or []
        )
        if not has_product:
            continue
        if status in _REVIEW_ELIGIBLE_ORDER_STATUSES:
            return "delivered"
        if status not in _CANCELLED_ORDER_STATUSES:
            awaiting = True
    return "awaiting_delivery" if awaiting else "none"


def _submit_product_review(request, product_id, customer_id):
    """Gửi đánh giá; đặt thông báo vào session."""
    review_state = _customer_product_review_state(request, product_id)
    if review_state == "awaiting_delivery":
        request.session["review_error"] = "Bạn chỉ có thể đánh giá sau khi đơn hàng được giao thành công."
        return
    if review_state != "delivered":
        request.session["review_error"] = "Bạn chỉ có thể đánh giá sản phẩm sau khi đã nhận hàng thành công."
        return

    reviews_payload = _get(
        f"{SVC['interaction_api']}/reviews/",
        request,
        params={"product_id": product_id},
        cache_ttl=0,
    )
    if any(str(r.get("customer_id")) == str(customer_id) for r in _list_data(reviews_payload)):
        request.session["review_error"] = "Bạn đã đánh giá sản phẩm này rồi."
        return

    try:
        rating = int(request.POST.get("rating", 0))
    except (TypeError, ValueError):
        rating = 0
    if rating < 1 or rating > 5:
        request.session["review_error"] = "Vui lòng chọn số sao từ 1 đến 5."
        return
    comment_text = request.POST.get("comment_text", "")
    payload = {
        "product_id": int(product_id),
        "customer_id": int(customer_id),
        "rating": rating,
        "comment_text": comment_text,
        "verified_purchase": True,
        "image_urls": [],
    }
    resp = _post(f"{SVC['interaction_api']}/reviews/", json=payload, request=request)
    if resp is not None and resp.status_code in (200, 201):
        track_behavior(request, customer_id, int(product_id), "review")
        request.session["review_success"] = "Cảm ơn bạn đã đánh giá sản phẩm!"
    else:
        request.session["review_error"] = "Không thể gửi đánh giá. Vui lòng thử lại sau."


def _review_summary(reviews):
    visible = [r for r in reviews if not r.get("is_hidden")]
    ratings = []
    for review in visible:
        try:
            ratings.append(int(review.get("rating", 0)))
        except (TypeError, ValueError):
            continue
    count = len(ratings)
    if not count:
        return {"count": 0, "average": 0.0}
    average = sum(ratings) / count
    return {"count": count, "average": round(average, 1)}


def _order_can_review(status):
    return str(status or "").upper() in _REVIEW_ELIGIBLE_ORDER_STATUSES


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
    page = payload.get("page", 1)
    total_pages = payload.get("total_pages", 1)
    search = request.GET.get("search", "")
    prev_page = payload.get("prev_page")
    next_page = payload.get("next_page")
    if prev_page is None and page > 1:
        prev_page = page - 1
    if next_page is None and page < total_pages:
        next_page = page + 1
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
    track_behavior(request, customer_id, product_id, action)


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


def _recommendation_order_ids(request, customer_id, limit=0):
    """Return product IDs sorted by recommendation score (limit=0 → all products)."""
    payload = _get(
        f"{SVC['recommender']}/recommendations/{customer_id}/",
        request,
        params={"limit": limit},
        cache_ttl=5,
    )
    if not isinstance(payload, dict):
        return []
    return payload.get("recommended_product_ids") or []


def _products_by_ids(request, product_ids):
    if not product_ids:
        return []
    calls = [
        (_get, (f"{SVC['product']}/products/{pid}/", request), {"cache_ttl": 30})
        for pid in product_ids
    ]
    results = _parallel_call(calls, max_workers=min(8, len(calls) or 1))
    by_id = {}
    for data in results:
        if isinstance(data, dict) and data.get("id") is not None:
            by_id[int(data["id"])] = data
    return [by_id[int(pid)] for pid in product_ids if int(pid) in by_id]


def _recommendation_products(request, customer_id, limit=6):
    ids = _recommendation_order_ids(request, customer_id, limit=limit)
    return _products_by_ids(request, ids)


def _customer_recommendation_products_page(request, customer_id, page=1, page_size=12):
    """Paginate all products ordered by recommendation score (highest first)."""
    all_ids = _recommendation_order_ids(request, customer_id, limit=0)
    if not all_ids:
        logger.warning(
            "[recommendations] empty order for customer=%s — falling back to newest products",
            customer_id,
        )
        payload, total_pages = _guest_product_payload(request, page=page, page_size=page_size)
        products = [_fmt_product(p) for p in _list_data(payload)]
        return products, total_pages, _total_count(payload)

    total_count = len(all_ids)
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    page_ids = all_ids[start:start + page_size]
    products = [_fmt_product(p) for p in _products_by_ids(request, page_ids)]
    return products, total_pages, total_count


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


def _home_flash_sale_products(request):
    payload = _get(
        f"{SVC['product']}/products/",
        request,
        params={"flash_sale": "true", "page_size": 50},
        cache_ttl=10,
    )
    return [_fmt_product(p) for p in _list_data(payload)]


def _chunk_list(items, size):
    if not items or size < 1:
        return []
    return [items[i:i + size] for i in range(0, len(items), size)]


def _guest_product_payload(request, page=1, page_size=12):
    payload = _get(
        f"{SVC['product']}/products/",
        request,
        params={"page": page, "page_size": page_size, "sort_by": "newest"},
        cache_ttl=10,
    )
    total_pages = 1
    if isinstance(payload, dict):
        total_pages = int(payload.get("total_pages") or 1)
    return payload, total_pages


def _guest_product_card_json(p):
    cat = p.get("category") or {}
    cat_name = cat.get("name", "") if isinstance(cat, dict) else ""
    return {
        "id": p.get("id"),
        "name": p.get("name", ""),
        "image_url": p.get("image_url") or "",
        "price_fmt": p.get("display_price_fmt") or _fmt_vnd(p.get("price", 0)),
        "category_name": cat_name,
    }


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
        customer_page_size = 12
        categories_payload = _get(f"{SVC['product']}/categories/", request, cache_ttl=300)
        flash_products = _home_flash_sale_products(request)
        recommendation_products, rec_total_pages, total_products = (
            _customer_recommendation_products_page(request, eid, page=1, page_size=customer_page_size)
            if eid else ([], 1, 0)
        )
        if not eid:
            products_payload = _get(
                f"{SVC['product']}/products/",
                request,
                params={"page": 1, "page_size": 1},
                cache_ttl=10,
            )
            total_products = _total_count(products_payload)
        return render(request, "home.html", {
            "total_products": total_products,
            "total_customers": 0,
            "total_orders": 0,
            "user": user,
            "is_customer": True,
            "is_guest": False,
            "is_storefront": True,
            "recommendation_products": recommendation_products,
            "products_total_pages": rec_total_pages,
            "products_page_size": customer_page_size,
            "flash_products": flash_products,
            "flash_pages": _chunk_list(flash_products, 4),
            "categories": _list_data(categories_payload),
            "category_pages": _chunk_list(_list_data(categories_payload), 6),
        })

    if role not in ("staff", "manager"):
        guest_page_size = 12
        guest_calls = [
            (_get, (f"{SVC['product']}/products/", request), {
                "params": {"page": 1, "page_size": guest_page_size, "sort_by": "newest"},
                "cache_ttl": 10,
            }),
            (_get, (f"{SVC['product']}/categories/", request), {"cache_ttl": 300}),
        ]
        guest_results = _parallel_call(guest_calls, max_workers=2)
        guest_products_payload, categories_payload = guest_results
        flash_products = _home_flash_sale_products(request)
        categories = _list_data(categories_payload)
        total_pages = 1
        if isinstance(guest_products_payload, dict):
            total_pages = int(guest_products_payload.get("total_pages") or 1)
        return render(request, "home.html", {
            "total_products": _total_count(guest_products_payload),
            "total_customers": 0,
            "total_orders": 0,
            "user": user,
            "is_customer": False,
            "is_guest": True,
            "is_storefront": True,
            "products": [_fmt_product(p) for p in _list_data(guest_products_payload)],
            "products_total_pages": total_pages,
            "products_page_size": guest_page_size,
            "categories": categories,
            "flash_products": flash_products,
            "flash_pages": _chunk_list(flash_products, 4),
            "category_pages": _chunk_list(categories, 6),
        })

    # Cache order list for 10s
    orders_payload = results[1] if len(results) > 1 else _get(f"{SVC['order']}/orders/", request, cache_ttl=10)
    return render(request, "home.html", {
        "total_products": total_products,
        "total_customers": 0,
        "total_orders": _total_count(orders_payload),
        "user": user,
        "is_customer": False,
        "is_guest": False,
        "is_storefront": False,
    })


def _home_products_api_response(request, page, page_size, customer_id=None):
    from django.http import JsonResponse

    if customer_id is not None:
        products, total_pages, total_count = _customer_recommendation_products_page(
            request, customer_id, page=page, page_size=page_size,
        )
        card_products = [_guest_product_card_json(p) for p in products]
        return JsonResponse({
            "products": card_products,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_more": page < total_pages,
            "total_count": total_count,
        })

    payload, total_pages = _guest_product_payload(request, page=page, page_size=page_size)
    products = [_guest_product_card_json(_fmt_product(p)) for p in _list_data(payload)]
    return JsonResponse({
        "products": products,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_more": page < total_pages,
        "total_count": _total_count(payload),
    })


def guest_products_api(request):
    """JSON API for guest infinite scroll on the home page."""
    from django.http import JsonResponse

    if _role(request):
        return JsonResponse({"error": "Unauthorized"}, status=401)

    try:
        page = max(1, int(request.GET.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = min(24, max(1, int(request.GET.get("page_size", 12))))
    except (TypeError, ValueError):
        page_size = 12

    return _home_products_api_response(request, page, page_size)


def home_products_api(request):
    """JSON API for customer infinite scroll on the home page (recommendation order)."""
    from django.http import JsonResponse

    if _role(request) != "customer":
        return JsonResponse({"error": "Unauthorized"}, status=401)

    customer_id = _entity_id(request)
    if customer_id is None:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    try:
        page = max(1, int(request.GET.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = min(24, max(1, int(request.GET.get("page_size", 12))))
    except (TypeError, ValueError):
        page_size = 12

    return _home_products_api_response(request, page, page_size, customer_id=customer_id)


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
    if "page_size" not in params:
        params["page_size"] = 14
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
    filter_query = {}
    for key in ("category_id", "min_price", "max_price", "sort_by"):
        val = request.GET.get(key)
        if val:
            filter_query[key] = val
    products_pagination = _pagination_context(products_payload, request, extra_query=filter_query)
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
        "is_guest": not role,
        "is_customer": role == "customer",
    })


def promotion_list(request):
    flash_products = _home_flash_sale_products(request)
    flash_sales_payload = _get(
        f"{SVC['promotion']}/api/promotions/flash-sales/",
        request,
        params={"active": "true"},
        cache_ttl=10,
    )
    flash_sales = _list_data(flash_sales_payload)

    voucher_payload = _get(f"{SVC['promotion']}/api/promotions/vouchers/", request, params={"active": "true"}, cache_ttl=10)
    vouchers = _list_data(voucher_payload)

    return render(request, "promotions.html", {
        "flash_sales": flash_sales,
        "flash_products": flash_products,
        "vouchers": vouchers,
        "user": request.session.get("user", {}),
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
        if request.POST.get("_action") == "review":
            _submit_product_review(request, product_id, customer_id)
            return redirect(f"/products/{product_id}/#reviews")
        quantity = int(request.POST.get("quantity", 1))
        formatted_product = _fmt_product(product)
        payload = {
            "product_id": int(product_id),
            "quantity": quantity,
            "unit_price": float(formatted_product.get("display_price") or 0),
        }
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
    reviews = [r for r in _list_data(reviews_payload) if not r.get("is_hidden")]
    review_summary = _review_summary(reviews)
    
    in_wishlist = False
    can_review = False
    already_reviewed = False
    awaiting_delivery = False
    if customer_id:
        wishlist_payload = _get(f"{SVC['interaction_api']}/wishlists/", request, params={"customer_id": customer_id, "product_id": product_id}, cache_ttl=0)
        in_wishlist = len(_list_data(wishlist_payload)) > 0
        already_reviewed = any(str(r.get("customer_id")) == str(customer_id) for r in reviews)
        review_state = _customer_product_review_state(request, product_id)
        awaiting_delivery = review_state == "awaiting_delivery"
        can_review = review_state == "delivered" and not already_reviewed
    
    return render(request, "product_detail.html", {
        "product": _fmt_product(product),
        "recommendations": [_fmt_product(r) for r in recommendations],
        "reviews": reviews,
        "review_summary": review_summary,
        "in_wishlist": in_wishlist,
        "is_customer": role == "customer",
        "is_guest": not role,
        "customer_id": customer_id,
        "can_review": can_review,
        "already_reviewed": already_reviewed,
        "awaiting_delivery": awaiting_delivery,
        "review_error": request.session.pop("review_error", None),
        "review_success": request.session.pop("review_success", None),
        "error": error,
    })

@require_roles("customer")
def product_review(request, product_id):
    """Legacy URL — chuyển về xử lý trên trang chi tiết sản phẩm."""
    if request.method == "POST":
        customer_id = _entity_id(request)
        if customer_id is not None:
            _submit_product_review(request, product_id, customer_id)
    return redirect(f"/products/{product_id}/#reviews")

@require_roles("customer")
def product_wishlist_toggle(request, product_id):
    if request.method == "POST":
        customer_id = _entity_id(request)
        wishlist_payload = _get(f"{SVC['interaction_api']}/wishlists/", request, params={"customer_id": customer_id, "product_id": product_id}, cache_ttl=0)
        items = _list_data(wishlist_payload)
        
        if items:
            _delete(f"{SVC['interaction_api']}/wishlists/{items[0]['id']}/", request)
        else:
            resp = _post(
                f"{SVC['interaction_api']}/wishlists/",
                json={"customer_id": customer_id, "product_id": product_id},
                request=request,
            )
            if resp is not None and resp.status_code in (200, 201):
                track_behavior(request, customer_id, int(product_id), "wishlist")
            
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
        if quantity < 1:
            return render(request, "cart.html", {
                "cart": _get(f"{SVC['cart']}/carts/{customer_id}/", request),
                "customer_id": customer_id,
                "products": _list_data(_get(f"{SVC['product']}/products/", request, params={"page_size": 500}, cache_ttl=10)),
                "error": "Số lượng phải lớn hơn 0.",
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

def _estimate_distance_km(request, city):
    if not city:
        return 10.0
    zone = _get(
        f"{SVC['ship']}/api/shipping/zones/",
        request,
        params={"city": city},
        cache_ttl=300,
    )
    if isinstance(zone, dict) and zone.get("distance_km") is not None:
        return float(zone["distance_km"])
    return 15.0


def _cart_weight(items):
    return sum(max(1, int(it.get("quantity", 1))) * 0.5 for it in items)


def _fetch_shipping_fee(request, method_id, items, city=None):
    distance_km = _estimate_distance_km(request, city)
    payload = {
        "shipping_method_id": int(method_id),
        "total_weight": _cart_weight(items),
        "distance_km": distance_km,
    }
    resp = _post(f"{SVC['ship']}/api/shipping/calculate-fee/", json=payload, request=request)
    if resp and resp.status_code == 200:
        data = resp.json()
        data["distance_km"] = distance_km
        return data
    return None


def _enrich_shipping_methods(request, methods, items, city=None):
    enriched = []
    for method in methods:
        fee_data = _fetch_shipping_fee(request, method["id"], items, city) if method.get("id") else None
        if fee_data is None:
            enriched.append({**method, "calculated_fee": None, "fee_error": True})
        else:
            enriched.append({**method, "calculated_fee": fee_data.get("shipping_fee"), "distance_km": fee_data.get("distance_km")})
    return enriched


def _hydrate_cart_items_with_products(items, product_map):
    hydrated = []
    for it in items:
        pid = it.get("product_id")
        prod = product_map.get(pid, {})
        formatted = _fmt_product(prod) if prod else {}
        variant_str = ""
        variant_name = ""
        if it.get("variant_id"):
            for v in prod.get("variants", []):
                if v.get("id") == it["variant_id"]:
                    variant_name = f"{v.get('color')} - {v.get('size')}"
                    variant_str = f" ({variant_name})"
                    break
        prod_name = prod.get("name") or f"Sản phẩm #{pid}"
        unit_price = formatted.get("display_price") if formatted else float(it.get("unit_price") or 0)
        row = {
            **it,
            "product_name": prod_name + variant_str,
            "variant_name": variant_name,
            "unit_price": unit_price,
        }
        if formatted.get("is_flash_sale_active"):
            row["flash_sale"] = True
            row["original_price"] = formatted.get("list_price")
            row["flash_sale_name"] = prod.get("flash_sale_name", "")
        hydrated.append(row)
    return hydrated


def _cart_subtotal(items):
    return sum(float(it.get("unit_price") or 0) * int(it.get("quantity") or 0) for it in items)


def _safe_return_url(request, param="next"):
    """Chỉ cho phép redirect nội bộ (path tương đối)."""
    raw = (request.GET.get(param) or request.POST.get(param) or "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme or parsed.netloc:
        return None
    if not raw.startswith("/"):
        return None
    return raw


def _append_query_param(url, key, value):
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query[key] = [str(value)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def _fetch_user_addresses(request, auth_user_id):
    if not auth_user_id:
        return []
    payload = _get(f"{SVC['user']}/internal/users/{auth_user_id}/addresses/", request, cache_ttl=0)
    return _list_data(payload) if isinstance(payload, list) else ([payload] if isinstance(payload, dict) and payload.get("id") else [])

def _resolve_user_address(request, auth_user_id, address_id):
    for a in _fetch_user_addresses(request, auth_user_id):
        if str(a.get("id")) == str(address_id):
            return a
    return None


def _validate_shipping_address_snapshot(snapshot):
    required = {
        "recipient_name": "tên người nhận",
        "phone": "số điện thoại",
        "address_line": "địa chỉ",
        "city": "thành phố",
    }
    if not snapshot:
        return "Vui lòng chọn địa chỉ giao hàng."
    for field, label in required.items():
        if not str(snapshot.get(field) or "").strip():
            return f"Địa chỉ giao hàng thiếu {label}."
    return None


def _checkout_page_context(request, customer_id, cart, items, auth_user_id, error=None, success=None):
    products_payload = _get(f"{SVC['product']}/products/", request, params={"page_size": 500}, cache_ttl=10)
    product_map = {b.get("id"): b for b in _list_data(products_payload) if isinstance(b, dict) and b.get("id") is not None}
    hydrated_items = _hydrate_cart_items_with_products(items, product_map)
    addresses = _fetch_user_addresses(request, auth_user_id)
    default_city = next((a.get("city") for a in addresses if a.get("is_default")), None)
    if not default_city and addresses:
        default_city = addresses[0].get("city")
    shipping_methods = _enrich_shipping_methods(
        request,
        _list_data(_get(f"{SVC['ship']}/api/methods/", request)),
        hydrated_items,
        default_city,
    )
    subtotal = _cart_subtotal(hydrated_items)
    profile_url = f"/profile/?next=/cart/{customer_id}/checkout/&from=checkout&action=add_address"
    return {
        "customer_id": customer_id,
        "cart": cart,
        "cart_items": hydrated_items,
        "addresses": addresses,
        "shipping_methods": shipping_methods,
        "subtotal": subtotal,
        "error": error,
        "success": success,
        "profile_add_address_url": profile_url,
    }


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

        validation_error = None
        if not address_id:
            validation_error = "Vui lòng chọn địa chỉ giao hàng."
        elif not shipping_method_id:
            validation_error = "Vui lòng chọn phương thức vận chuyển."
        elif not auth_user_id:
            validation_error = "Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại."

        address_snapshot = None
        city = None
        if not validation_error:
            address_snapshot = _resolve_user_address(request, auth_user_id, address_id)
            if not address_snapshot:
                validation_error = "Địa chỉ giao hàng không hợp lệ hoặc đã bị xóa."
            else:
                validation_error = _validate_shipping_address_snapshot(address_snapshot)
                if not validation_error:
                    city = address_snapshot.get("city")

        shipping_method_name = ""
        if not validation_error:
            methods = _list_data(_get(f"{SVC['ship']}/api/methods/", request))
            for m in methods:
                if str(m.get("id")) == str(shipping_method_id):
                    shipping_method_name = m.get("method_name") or ""
                    break
            if not shipping_method_name:
                validation_error = "Phương thức vận chuyển không hợp lệ."

        if validation_error:
            ctx = _checkout_page_context(request, customer_id, cart, items, auth_user_id, error=validation_error)
            return render(request, "checkout.html", ctx)

        fee_data = _fetch_shipping_fee(request, shipping_method_id, items, city)
        if not fee_data or fee_data.get("shipping_fee") is None:
            ctx = _checkout_page_context(
                request, customer_id, cart, items, auth_user_id,
                error="Không tính được phí vận chuyển. Vui lòng thử lại sau.",
            )
            return render(request, "checkout.html", ctx)
        shipping_fee = fee_data.get("shipping_fee")
        distance_km = fee_data.get("distance_km")

        products_payload = _get(f"{SVC['product']}/products/", request, params={"page_size": 500}, cache_ttl=10)
        product_map = {b.get("id"): b for b in _list_data(products_payload) if isinstance(b, dict) and b.get("id") is not None}
        order_items = _hydrate_cart_items_with_products(items, product_map)

        for it in order_items:
            if not it.get("product_id"):
                ctx = _checkout_page_context(request, customer_id, cart, items, auth_user_id, error="Giỏ hàng có sản phẩm không hợp lệ.")
                return render(request, "checkout.html", ctx)
            if int(it.get("quantity", 0)) <= 0:
                ctx = _checkout_page_context(request, customer_id, cart, items, auth_user_id, error="Số lượng sản phẩm phải lớn hơn 0.")
                return render(request, "checkout.html", ctx)
            if float(it.get("unit_price", 0)) <= 0:
                ctx = _checkout_page_context(request, customer_id, cart, items, auth_user_id, error="Giá sản phẩm không hợp lệ. Vui lòng cập nhật giỏ hàng.")
                return render(request, "checkout.html", ctx)

        address_snapshot = {
            **address_snapshot,
            "shipping_method_id": int(shipping_method_id),
            "shipping_method_name": shipping_method_name,
            "distance_km": distance_km,
        }

        payload = {
            "customer_id": customer_id,
            "items": [
                {
                    "product_id": it["product_id"],
                    "variant_id": it.get("variant_id"),
                    "product_name": it.get("product_name"),
                    "variant_name": it.get("variant_name"),
                    "quantity": it["quantity"],
                    "unit_price": float(it.get("unit_price", 0)),
                    "discount": float(it.get("original_price", 0) - it.get("unit_price", 0))
                    if it.get("flash_sale") and it.get("original_price") else 0,
                } for it in order_items
            ],
            "shipping_fee": shipping_fee,
            "shipping_method_id": int(shipping_method_id),
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
        ctx = _checkout_page_context(request, customer_id, cart, items, auth_user_id, error=err)
        return render(request, "checkout.html", ctx)

    success = None
    if request.GET.get("address_added") == "1":
        success = "Đã thêm địa chỉ giao hàng. Bạn có thể tiếp tục đặt hàng."
    address_error = request.GET.get("address_error")

    ctx = _checkout_page_context(request, customer_id, cart, items, auth_user_id, success=success, error=address_error)
    response = render(request, "checkout.html", ctx)
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["Pragma"] = "no-cache"
    return response

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
            track_order_purchases(request, order)
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
        paid_order = _get(f"{SVC['order']}/orders/{order_id}/", request)
        track_order_purchases(request, paid_order)
    elif status == "CANCELLED":
        request.session["order_success"] = f"Bạn đã hủy thanh toán đơn #{order_id}."
    else:
        request.session["order_success"] = f"Thanh toán đơn #{order_id} thất bại!"
        
    return redirect("order_list")


# ── Orders ────────────────────────────────────────────────────────────────────

def _customer_display_from_profile(data):
    if not isinstance(data, dict):
        return None
    for key in ("full_name", "username"):
        value = (data.get(key) or "").strip()
        if value:
            return value
    phone = (data.get("phone") or "").strip()
    return phone or None


def _customer_name_map(request):
    """Map customer_id -> tên hiển thị (full_name, username hoặc SĐT)."""
    customers = _list_data(_get(f"{SVC['user']}/internal/customers/", request, cache_ttl=60))
    name_map = {}
    for customer in customers:
        cid = customer.get("id") or customer.get("entity_id")
        if cid is None:
            continue
        display = _customer_display_from_profile(customer)
        if display:
            name_map[int(cid)] = display
    return name_map


def _fetch_customer_display_name(request, customer_id):
    if customer_id is None:
        return None
    try:
        customer_id = int(customer_id)
    except (TypeError, ValueError):
        return None
    data = _get(f"{SVC['user']}/internal/customers/{customer_id}/", request, cache_ttl=60)
    return _customer_display_from_profile(data)


def _session_customer_display(request, customer_id):
    user = _user(request)
    try:
        entity_id = int(user.get("entity_id") or 0)
    except (TypeError, ValueError):
        entity_id = 0
    if entity_id != int(customer_id):
        return None
    return (user.get("full_name") or user.get("username") or "").strip() or None


def _resolve_customer_display_name(request, customer_id, name_map=None):
    if customer_id is None:
        return None
    try:
        cid = int(customer_id)
    except (TypeError, ValueError):
        return None
    if name_map and cid in name_map:
        return name_map[cid]
    display = _fetch_customer_display_name(request, cid)
    if display:
        return display
    return _session_customer_display(request, cid)


def _enrich_with_customer_names(request, items, id_field="customer_id", name_field="customer_name"):
    if not items:
        return items
    customer_ids = {item.get(id_field) for item in items if item.get(id_field) is not None}
    if not customer_ids:
        return items

    name_map = _customer_name_map(request)
    missing = {int(cid) for cid in customer_ids} - set(name_map.keys())
    if missing:
        calls = [
            (_get, (f"{SVC['user']}/internal/customers/{cid}/",), {"cache_ttl": 60})
            for cid in sorted(missing)
        ]
        results = _parallel_call(calls, max_workers=min(8, len(calls)))
        for cid, data in zip(sorted(missing), results):
            display = _customer_display_from_profile(data)
            if display:
                name_map[cid] = display

    enriched = []
    for item in items:
        cid = item.get(id_field)
        display = name_map.get(int(cid)) if cid is not None else None
        if not display and cid is not None:
            display = _session_customer_display(request, cid)
        enriched.append({**item, name_field: display})
    return enriched


def _enrich_orders_with_customer_name(request, orders):
    return _enrich_with_customer_names(request, orders)

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
    if not customer_name:
        customer_name = _resolve_customer_display_name(request, customer_id)
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
            if status_raw in ('paid', 'PAID', 'COMPLETED', 'WAITING_INVENTORY_CONFIRM', 'PROCESSING', 'SHIPPING'):
                badge = "badge-info"
            elif status_raw in ("delivered", "DELIVERED"):
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

    if _role(request) == "customer":
        eid = _entity_id(request)
        try:
            order_customer_id = int(order.get("customer_id", 0))
        except (TypeError, ValueError):
            order_customer_id = 0
        if eid is None or order_customer_id != eid:
            return render(request, "403.html", {"message": "Bạn chỉ được xem đơn hàng của mình."}, status=403)

    items = order.get("items", [])
    hydrated_items = []
    for it in items:
        pid = it.get("product_id")
        name = (it.get("product_name") or "").strip() or f"Sản phẩm #{pid}"
        variant_name = (it.get("variant_name") or "").strip()
        if variant_name and variant_name not in name:
            name = f"{name} ({variant_name})"
        qty = int(it.get("quantity") or 0)
        unit_price = float(it.get("unit_price") or 0)
        hydrated_items.append({
            **it,
            "product_name": name,
            "unit_price_fmt": _fmt_vnd(unit_price),
            "line_total_fmt": _fmt_vnd(unit_price * qty),
        })
    order["items"] = hydrated_items

    order = _enrich_orders_with_customer_name(request, [order])[0]

    snapshot = order.get("shipping_address_snapshot") or {}
    if not snapshot.get("shipping_method_name") and snapshot.get("shipping_method_id"):
        for m in _list_data(_get(f"{SVC['ship']}/api/methods/", request)):
            if str(m.get("id")) == str(snapshot.get("shipping_method_id")):
                snapshot = {**snapshot, "shipping_method_name": m.get("method_name") or ""}
                order["shipping_address_snapshot"] = snapshot
                break

    shipping = _get(f"{SVC['ship']}/api/shippings/order/{order_id}/", request)
    has_shipping = isinstance(shipping, dict) and "error" not in shipping and shipping.get("id")

    return render(request, "order_detail.html", {
        "order": _fmt_order(order),
        "is_customer": _role(request) == "customer",
        "has_shipping": bool(has_shipping),
        "shipping_status": shipping.get("status") if has_shipping else None,
        "can_review_order": _order_can_review(order.get("status")),
    })

# ── Recommendations ───────────────────────────────────────────────────────────

@require_customer_or_staff
def recommendation_list(request):
    """Đề xuất AI hiển thị trên trang chủ — chuyển hướng về home."""
    if _role(request) != "customer":
        return render(request, "403.html", {"message": "Trang này chỉ dành cho khách hàng."}, status=403)
    return redirect("home")


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
def addresses_api(request):
    """API JSON danh sách địa chỉ — dùng cho cập nhật realtime trên checkout."""
    from django.http import JsonResponse
    user_id = request.session.get("user", {}).get("id")
    addresses = _fetch_user_addresses(request, user_id)
    response = JsonResponse({"addresses": addresses, "count": len(addresses)})
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@require_customer_or_staff
@customer_can_only_own("customer_id")
def checkout_apply_voucher_api(request, customer_id):
    """API JSON kiểm tra mã giảm giá trên checkout."""
    from django.http import JsonResponse
    code = (request.GET.get("code") or request.POST.get("code") or "").strip()
    if not code:
        return JsonResponse({"error": "Vui lòng nhập mã giảm giá."}, status=400)

    cart = _get(f"{SVC['cart']}/carts/{customer_id}/", request, cache_ttl=0)
    items = (cart or {}).get("items") if isinstance(cart, dict) else []
    if not items:
        return JsonResponse({"error": "Giỏ hàng trống."}, status=400)

    products_payload = _get(f"{SVC['product']}/products/", request, params={"page_size": 500}, cache_ttl=10)
    product_map = {
        b.get("id"): b for b in _list_data(products_payload)
        if isinstance(b, dict) and b.get("id") is not None
    }
    hydrated = _hydrate_cart_items_with_products(items, product_map)
    subtotal = _cart_subtotal(hydrated)

    resp = _post(
        f"{SVC['promotion']}/api/promotions/apply-voucher/",
        json={"code": code, "order_amount": subtotal},
        request=request,
    )
    if resp is None:
        return JsonResponse({"error": "Không thể kết nối dịch vụ khuyến mãi."}, status=503)
    if resp.status_code != 200:
        err = resp.json().get("error", "Mã giảm giá không hợp lệ.") if resp.content else "Mã giảm giá không hợp lệ."
        return JsonResponse({"error": err}, status=resp.status_code)

    data = resp.json()
    discount = float(data.get("discount_amount", 0))
    response = JsonResponse({
        "code": data.get("code", code),
        "discount_amount": discount,
        "discount_amount_fmt": _fmt_vnd(discount),
        "subtotal": subtotal,
        "subtotal_fmt": _fmt_vnd(subtotal),
        "final_amount": float(data.get("final_amount", subtotal - discount)),
    })
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@require_customer_or_staff
@customer_can_only_own("customer_id")
def checkout_shipping_fees_api(request, customer_id):
    """API JSON phí vận chuyển theo thành phố — cập nhật realtime khi chọn địa chỉ."""
    from django.http import JsonResponse
    city = request.GET.get("city", "")
    cart = _get(f"{SVC['cart']}/carts/{customer_id}/", request, cache_ttl=0)
    items = (cart or {}).get("items") if isinstance(cart, dict) else []
    if not items:
        return JsonResponse({"methods": []})
    products_payload = _get(f"{SVC['product']}/products/", request, params={"page_size": 500}, cache_ttl=10)
    product_map = {b.get("id"): b for b in _list_data(products_payload) if isinstance(b, dict) and b.get("id") is not None}
    hydrated_items = _hydrate_cart_items_with_products(items, product_map)
    methods = _enrich_shipping_methods(
        request,
        _list_data(_get(f"{SVC['ship']}/api/methods/", request)),
        hydrated_items,
        city or None,
    )
    response = JsonResponse({"methods": methods})
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@require_auth
def profile_view(request):
    user_id = request.session.get("user", {}).get("id")
    profile = _get(f"{SVC['user']}/internal/users/{user_id}/", request, cache_ttl=0)
    addresses = _fetch_user_addresses(request, user_id)
    return_url = _safe_return_url(request)
    response = render(request, "profile.html", {
        "profile": profile,
        "addresses": addresses,
        "return_url": return_url,
        "from_checkout": request.GET.get("from") == "checkout",
        "auto_add_address": request.GET.get("action") == "add_address",
        "address_added": request.GET.get("address_added") == "1",
    })
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


def _validate_address_form(data):
    required = {
        "recipient_name": "Họ và tên người nhận",
        "phone": "Số điện thoại",
        "city": "Tỉnh/Thành phố",
        "address_line": "Địa chỉ chi tiết",
    }
    for field, label in required.items():
        if not str(data.get(field) or "").strip():
            return f"{label} là bắt buộc."
    return None


@require_auth
def address_add(request):
    next_url = _safe_return_url(request)
    if request.method == "POST":
        user_id = request.session.get("user", {}).get("id")
        payload = {
            "recipient_name": request.POST.get("recipient_name", "").strip(),
            "phone": request.POST.get("phone", "").strip(),
            "address_line": request.POST.get("address_line", "").strip(),
            "city": request.POST.get("city", "").strip(),
            "state": request.POST.get("state", "").strip(),
            "country": request.POST.get("country", "VN"),
            "postal_code": request.POST.get("postal_code", "000000"),
            "is_default": request.POST.get("is_default") == "on",
        }
        form_error = _validate_address_form(payload)
        if form_error:
            if next_url:
                return redirect(_append_query_param(next_url, "address_error", form_error))
            return redirect(_append_query_param("/profile/", "address_error", form_error))

        resp = _post(f"{SVC['user']}/internal/users/{user_id}/addresses/", json=payload, request=request)
        if resp is not None and resp.status_code in (200, 201):
            if next_url:
                return redirect(_append_query_param(next_url, "address_added", "1"))
        elif next_url:
            err = _response_error(resp, "Không thể lưu địa chỉ")
            msg = err.get("error") if isinstance(err, dict) else str(err)
            return redirect(_append_query_param(next_url, "address_error", msg))

    if next_url:
        return redirect(next_url)
    return redirect("profile")


@require_auth
def address_delete(request, address_id):
    next_url = _safe_return_url(request)
    if request.method == "POST":
        user_id = request.session.get("user", {}).get("id")
        _delete(f"{SVC['user']}/internal/users/{user_id}/addresses/{address_id}/", request)
    if next_url:
        return redirect(next_url)
    return redirect("profile")


@require_auth
def address_set_default(request, address_id):
    next_url = _safe_return_url(request)
    if request.method == "POST":
        user_id = request.session.get("user", {}).get("id")
        _post(f"{SVC['user']}/internal/users/{user_id}/addresses/{address_id}/", json={"is_default": True}, request=request, method="PUT")
    if next_url:
        return redirect(next_url)
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

def _serialize_ticket_replies(ticket):
    replies = ticket.get("replies") or []
    return [
        {
            "id": str(r.get("id")),
            "sender_id": r.get("sender_id"),
            "is_staff": bool(r.get("is_staff")),
            "message": r.get("message") or "",
            "created_at": r.get("created_at"),
        }
        for r in replies
    ]


TICKET_STATUS_VI = {
    "OPEN": "Chờ xử lý",
    "IN_PROGRESS": "Đang xử lý",
    "RESOLVED": "Đã giải quyết",
    "CLOSED": "Đã đóng",
}

TICKET_STATUS_BADGE = {
    "OPEN": "badge-danger",
    "IN_PROGRESS": "badge-info",
    "RESOLVED": "badge-success",
    "CLOSED": "badge-secondary",
}


def _vi_ticket_status(status):
    if not status:
        return "—"
    key = str(status).strip().upper().replace("-", "_")
    return TICKET_STATUS_VI.get(key, key.replace("_", " ").lower().capitalize())


def ticket_chat_payload(ticket):
    status = (ticket.get("status") or "OPEN").upper()
    return {
        "ticket_id": str(ticket.get("id")),
        "status": status,
        "status_label": _vi_ticket_status(status),
        "status_badge": TICKET_STATUS_BADGE.get(status, "badge-secondary"),
        "subject": ticket.get("subject"),
        "content": ticket.get("content"),
        "created_at": ticket.get("created_at"),
        "order_id": ticket.get("order_id"),
        "can_reply": status != "CLOSED",
        "replies": _serialize_ticket_replies(ticket),
    }


def _parse_chat_message(request):
    import json as _json
    if request.content_type and "application/json" in request.content_type:
        try:
            body = _json.loads(request.body or b"{}")
        except Exception:
            body = {}
        return (body.get("message") or "").strip()
    return (request.POST.get("message") or "").strip()


def _post_ticket_reply(request, ticket_id, sender_id, is_staff, message):
    return _post(
        f"{SVC['interaction_api']}/ticket-replies/",
        json={
            "ticket": ticket_id,
            "sender_id": sender_id,
            "is_staff": is_staff,
            "message": message,
        },
        request=request,
    )


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

    return render(request, "support/detail.html", {
        "ticket": ticket,
        "chat_api_url": f"/support/{ticket_id}/api/messages/",
    })


@require_auth
def support_ticket_messages_api(request, ticket_id):
    from django.http import JsonResponse

    customer_id = _entity_id(request)
    ticket = _get(f"{SVC['interaction_api']}/tickets/{ticket_id}/", request)
    if not ticket or ticket.get("customer_id") != customer_id:
        return JsonResponse({"error": "Forbidden"}, status=403)

    if request.method == "POST":
        message = _parse_chat_message(request)
        if not message:
            return JsonResponse({"error": "Tin nhắn không được để trống."}, status=400)
        if ticket.get("status") == "CLOSED":
            return JsonResponse({"error": "Ticket đã đóng."}, status=400)
        resp = _post_ticket_reply(request, ticket_id, customer_id, False, message)
        if not resp or resp.status_code not in (200, 201):
            return JsonResponse({"error": "Không gửi được tin nhắn."}, status=502)
        ticket = _get(f"{SVC['interaction_api']}/tickets/{ticket_id}/", request, cache_ttl=0)

    return JsonResponse(ticket_chat_payload(ticket))
