import json
from collections import defaultdict
from datetime import datetime, timedelta

from django.shortcuts import render, redirect
from django.contrib import messages
from .views import (
    _get, _post, _delete, _role, _entity_id, _total_count, _list_data, _fmt_vnd, SVC,
    ORDER_STATUS_VI,
    _enrich_orders_with_customer_name, _enrich_with_customer_names, _resolve_customer_display_name,
    ticket_chat_payload, _parse_chat_message, _post_ticket_reply,
)
from .permissions import require_staff, require_manager

INTERACTION = SVC["interaction_api"]

LOW_STOCK_THRESHOLD = 10
_REVENUE_STATUSES = frozenset({"DELIVERED", "PAID", "PROCESSING", "SHIPPING"})
_CHART_COLORS = [
    "#2563EB", "#7C3AED", "#10B981", "#F59E0B", "#EF4444",
    "#06B6D4", "#8B5CF6", "#F97316", "#14B8A6", "#EC4899",
]
_TICKET_STATUS_VI = {
    "OPEN": "Chờ xử lý",
    "IN_PROGRESS": "Đang xử lý",
    "RESOLVED": "Đã giải quyết",
    "CLOSED": "Đã đóng",
}
_WEEKDAY_VI = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]


def _parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).strip()
    for fmt, length in (
        ("%Y-%m-%dT%H:%M:%S.%f", 26),
        ("%Y-%m-%dT%H:%M:%S", 19),
        ("%Y-%m-%d %H:%M:%S.%f", 26),
        ("%Y-%m-%d %H:%M:%S", 19),
        ("%Y-%m-%d", 10),
    ):
        try:
            return datetime.strptime(s[:length], fmt)
        except ValueError:
            continue
    return None


def _fetch_all_orders(request, page_size=200):
    first = _get(
        f"{SVC['order']}/orders/",
        request,
        params={"page_size": page_size},
        cache_ttl=10,
    )
    if not isinstance(first, dict):
        return _list_data(first)
    orders = list(first.get("results") or [])
    total_pages = int(first.get("total_pages", 1) or 1)
    for page in range(2, total_pages + 1):
        payload = _get(
            f"{SVC['order']}/orders/",
            request,
            params={"page": page, "page_size": page_size},
            cache_ttl=10,
        )
        orders.extend(_list_data(payload))
    return orders


def _fetch_all_products(request, page_size=200):
    first = _get(
        f"{SVC['product']}/products/",
        request,
        params={"page_size": page_size},
        cache_ttl=30,
    )
    if not isinstance(first, dict):
        return _list_data(first)
    products = list(first.get("results") or [])
    total_pages = int(first.get("total_pages", 1) or 1)
    for page in range(2, total_pages + 1):
        payload = _get(
            f"{SVC['product']}/products/",
            request,
            params={"page": page, "page_size": page_size},
            cache_ttl=30,
        )
        products.extend(_list_data(payload))
    return products


def _day_labels(days):
    labels = []
    for d in days:
        wd = _WEEKDAY_VI[d.weekday()]
        labels.append(f"{wd} {d.strftime('%d/%m')}")
    return labels


def _build_admin_analytics(request):
    metrics = _get(f"{SVC['order']}/orders/metrics/", request) or {}
    orders = _fetch_all_orders(request)
    products = _fetch_all_products(request)
    customers = _list_data(_get(f"{SVC['user']}/internal/customers/", request))
    tickets = _list_data(_get(f"{SVC['interaction_api']}/tickets/", request))
    vouchers = _list_data(_get(f"{SVC['promotion']}/api/promotions/vouchers/", request))
    flash_sales = _list_data(_get(f"{SVC['promotion']}/api/promotions/flash-sales/", request))

    status_breakdown = metrics.get("status_breakdown", {})
    total_orders = metrics.get("total_orders", len(orders))
    total_revenue_raw = float(metrics.get("total_revenue", 0) or 0)
    delivered_orders = status_breakdown.get("DELIVERED", 0)
    cancelled_orders = status_breakdown.get("CANCELLED", 0)

    today = datetime.now().date()
    last_7 = [today - timedelta(days=i) for i in range(6, -1, -1)]
    last_30 = [today - timedelta(days=i) for i in range(29, -1, -1)]
    last_6_months = []
    cursor = today.replace(day=1)
    for _ in range(6):
        last_6_months.insert(0, cursor)
        cursor = (cursor - timedelta(days=1)).replace(day=1)

    revenue_7 = {d.isoformat(): 0.0 for d in last_7}
    orders_7 = {d.isoformat(): 0 for d in last_7}
    revenue_30 = {d.isoformat(): 0.0 for d in last_30}
    orders_30 = {d.isoformat(): 0 for d in last_30}
    orders_by_hour = {h: 0 for h in range(24)}
    order_value_buckets = {"< 500K": 0, "500K–1M": 0, "1M–3M": 0, "3M–5M": 0, "> 5M": 0}

    product_qty = defaultdict(int)
    product_revenue = defaultdict(float)
    category_sales = defaultdict(float)
    brand_sales = defaultdict(float)
    product_map = {p["id"]: p for p in products}

    for order in orders:
        dt = _parse_dt(order.get("order_date") or order.get("created_at"))
        status = str(order.get("status", "")).upper()
        amount = float(order.get("total_amount") or 0)

        if dt:
            day_key = dt.date().isoformat()
            if day_key in orders_7:
                orders_7[day_key] += 1
            if day_key in orders_30:
                orders_30[day_key] += 1
            if status == "DELIVERED":
                if day_key in revenue_7:
                    revenue_7[day_key] += amount
                if day_key in revenue_30:
                    revenue_30[day_key] += amount
            orders_by_hour[dt.hour] += 1

        if status == "DELIVERED":
            if amount < 500_000:
                order_value_buckets["< 500K"] += 1
            elif amount < 1_000_000:
                order_value_buckets["500K–1M"] += 1
            elif amount < 3_000_000:
                order_value_buckets["1M–3M"] += 1
            elif amount < 5_000_000:
                order_value_buckets["3M–5M"] += 1
            else:
                order_value_buckets["> 5M"] += 1

        if status in _REVENUE_STATUSES:
            for item in order.get("items") or []:
                pid = item.get("product_id")
                if not pid:
                    continue
                qty = int(item.get("quantity", 0) or 0)
                line_total = float(item.get("unit_price", 0) or 0) * qty
                product_qty[pid] += qty
                product_revenue[pid] += line_total
                prod = product_map.get(pid, {})
                cat_name = (prod.get("category") or {}).get("name", "Khác")
                brand_name = (prod.get("brand") or {}).get("name", "Không thương hiệu")
                category_sales[cat_name] += line_total
                brand_sales[brand_name] += line_total

    top_by_qty = sorted(product_qty.items(), key=lambda x: x[1], reverse=True)[:8]
    top_by_revenue = sorted(product_revenue.items(), key=lambda x: x[1], reverse=True)[:8]
    top_sellers = [
        {
            "id": pid,
            "name": product_map.get(pid, {}).get("name", f"Sản phẩm #{pid}"),
            "qty": qty,
            "revenue": product_revenue.get(pid, 0),
        }
        for pid, qty in top_by_qty
    ]

    in_stock = low_stock = out_of_stock = 0
    low_stock_products = []
    for p in products:
        stock = int(p.get("stock") or 0)
        if stock == 0:
            out_of_stock += 1
            low_stock_products.append(p)
        elif stock <= LOW_STOCK_THRESHOLD:
            low_stock += 1
            low_stock_products.append(p)
        else:
            in_stock += 1
    low_stock_products.sort(key=lambda p: int(p.get("stock") or 0))

    ticket_status = defaultdict(int)
    for ticket in tickets:
        ticket_status[str(ticket.get("status", "OPEN")).upper()] += 1

    customers_by_month = {m.strftime("%Y-%m"): 0 for m in last_6_months}
    new_customers_30d = 0
    cutoff_30d = today - timedelta(days=30)
    for customer in customers:
        dt = _parse_dt(customer.get("created_at"))
        if not dt:
            continue
        if dt.date() >= cutoff_30d:
            new_customers_30d += 1
        month_key = dt.strftime("%Y-%m")
        if month_key in customers_by_month:
            customers_by_month[month_key] += 1

    status_labels, status_values = [], []
    for status, count in sorted(status_breakdown.items(), key=lambda x: -x[1]):
        status_labels.append(ORDER_STATUS_VI.get(status, status.replace("_", " ").title()))
        status_values.append(count)

    category_sorted = sorted(category_sales.items(), key=lambda x: -x[1])[:8]
    brand_sorted = sorted(brand_sales.items(), key=lambda x: -x[1])[:8]
    ticket_sorted = sorted(ticket_status.items(), key=lambda x: -x[1])

    recent_orders = sorted(
        orders,
        key=lambda o: _parse_dt(o.get("order_date") or o.get("created_at")) or datetime.min,
        reverse=True,
    )[:8]

    aov = total_revenue_raw / delivered_orders if delivered_orders else 0
    delivery_rate = round(delivered_orders / total_orders * 100, 1) if total_orders else 0
    cancel_rate = round(cancelled_orders / total_orders * 100, 1) if total_orders else 0
    open_tickets = ticket_status.get("OPEN", 0) + ticket_status.get("IN_PROGRESS", 0)

    chart_data = {
        "revenue7": {
            "labels": _day_labels(last_7),
            "values": [revenue_7[d.isoformat()] for d in last_7],
        },
        "orders7": {
            "labels": _day_labels(last_7),
            "values": [orders_7[d.isoformat()] for d in last_7],
        },
        "revenue30": {
            "labels": [d.strftime("%d/%m") for d in last_30],
            "values": [revenue_30[d.isoformat()] for d in last_30],
        },
        "orders30": {
            "labels": [d.strftime("%d/%m") for d in last_30],
            "values": [orders_30[d.isoformat()] for d in last_30],
        },
        "statusBreakdown": {"labels": status_labels, "values": status_values},
        "topProductsQty": {
            "labels": [product_map.get(pid, {}).get("name", f"SP #{pid}")[:28] for pid, _ in top_by_qty],
            "values": [qty for _, qty in top_by_qty],
        },
        "topProductsRevenue": {
            "labels": [product_map.get(pid, {}).get("name", f"SP #{pid}")[:28] for pid, _ in top_by_revenue],
            "values": [round(product_revenue[pid]) for pid, _ in top_by_revenue],
        },
        "categorySales": {
            "labels": [name for name, _ in category_sorted],
            "values": [round(val) for _, val in category_sorted],
        },
        "brandSales": {
            "labels": [name for name, _ in brand_sorted],
            "values": [round(val) for _, val in brand_sorted],
        },
        "ticketStatus": {
            "labels": [_TICKET_STATUS_VI.get(s, s) for s, _ in ticket_sorted],
            "values": [c for _, c in ticket_sorted],
        },
        "stockHealth": {
            "labels": ["Còn hàng", "Sắp hết", "Hết hàng"],
            "values": [in_stock, low_stock, out_of_stock],
        },
        "customerGrowth": {
            "labels": [m.strftime("%m/%Y") for m in last_6_months],
            "values": [customers_by_month[m.strftime("%Y-%m")] for m in last_6_months],
        },
        "ordersByHour": {
            "labels": [f"{h:02d}h" for h in range(24)],
            "values": [orders_by_hour[h] for h in range(24)],
        },
        "orderValueBuckets": {
            "labels": list(order_value_buckets.keys()),
            "values": list(order_value_buckets.values()),
        },
        "colors": _CHART_COLORS,
    }

    return {
        "metrics": metrics,
        "status_breakdown": status_breakdown,
        "total_orders": total_orders,
        "total_revenue": _fmt_vnd(total_revenue_raw),
        "total_revenue_raw": total_revenue_raw,
        "total_products": len(products),
        "total_customers": len(customers),
        "delivered_orders": delivered_orders,
        "cancelled_orders": cancelled_orders,
        "pending_revenue_orders": (
            status_breakdown.get("PENDING_PAYMENT", 0)
            + status_breakdown.get("PAID", 0)
            + status_breakdown.get("PROCESSING", 0)
            + status_breakdown.get("SHIPPING", 0)
        ),
        "avg_order_value": _fmt_vnd(aov),
        "delivery_rate": delivery_rate,
        "cancel_rate": cancel_rate,
        "open_tickets": open_tickets,
        "total_tickets": len(tickets),
        "low_stock_count": low_stock + out_of_stock,
        "new_customers_30d": new_customers_30d,
        "promotion_count": len(vouchers) + len(flash_sales),
        "top_sellers": top_sellers,
        "low_stock_products": low_stock_products[:10],
        "recent_orders": recent_orders,
        "chart_data_json": json.dumps(chart_data),
    }


# ── Dashboard & Reports (Phase 4) ─────────────────────────────────────────
@require_manager
def admin_dashboard(request):
    ctx = _build_admin_analytics(request)
    ctx["role"] = _role(request)
    return render(request, "admin/dashboard.html", ctx)


@require_manager
def admin_reports(request):
    ctx = _build_admin_analytics(request)
    ctx["role"] = _role(request)
    return render(request, "admin/reports.html", ctx)


@require_manager
def admin_recommendation(request):
    models_data = _get(f"{SVC['recommender']}/api/v1/models/", request) or {}
    retrain_status = _get(f"{SVC['recommender']}/api/v1/models/retrain/status/", request) or {}

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "retrain":
            resp = _post(f"{SVC['recommender']}/api/v1/models/retrain/", json={"model_type": "IMPLICIT_CF"}, request=request)
            if resp and resp.status_code == 200:
                messages.success(request, "Đã bắt đầu huấn luyện lại model.")
            elif resp and resp.status_code == 409:
                messages.warning(request, "Huấn luyện đang chạy, vui lòng đợi.")
            else:
                messages.error(request, "Không thể kích hoạt huấn luyện.")
        elif action == "activate":
            model_id = request.POST.get("model_id")
            if model_id:
                resp = _post(f"{SVC['recommender']}/api/v1/models/activate/", json={"model_id": model_id}, request=request)
                if resp and resp.status_code == 200:
                    messages.success(request, "Đã kích hoạt model.")
                else:
                    messages.error(request, "Không thể kích hoạt model.")
        elif action == "rollback":
            model_version = request.POST.get("model_version")
            if model_version:
                resp = _post(f"{SVC['recommender']}/api/v1/models/rollback", json={"model_version": model_version}, request=request)
                if resp and resp.status_code == 200:
                    messages.success(request, "Đã rollback model.")
                else:
                    messages.error(request, "Rollback thất bại.")
        return redirect("admin_recommendation")

    offline_eval = models_data.get("offline_evaluation", {})
    return render(request, "admin/recommendation.html", {
        "role": _role(request),
        "versions": models_data.get("versions", []),
        "offline_models": offline_eval.get("models", []),
        "best_model": offline_eval.get("best_model"),
        "retrain_running": retrain_status.get("running", False),
    })


# ── Brands ──────────────────────────────────────────────────────────────
@require_staff
def admin_brand_list(request):
    brands = _list_data(_get(f"{SVC['product']}/brands/", request))
    return render(request, "admin/brands.html", {"brands": brands, "role": _role(request)})

@require_staff
def admin_brand_create(request):
    if request.method == "POST":
        payload = {
            "name": request.POST.get("name"),
            "description": request.POST.get("description", "")
        }
        _post(f"{SVC['product']}/brands/", json=payload, request=request)
        return redirect("admin_brand_list")
    return render(request, "admin/brand_form.html", {"role": _role(request)})

@require_staff
def admin_brand_edit(request, brand_id):
    brand = _get(f"{SVC['product']}/brands/{brand_id}/", request)
    if not isinstance(brand, dict) or not brand.get("id"):
        return render(request, "403.html", {"message": "Không tìm thấy thương hiệu."}, status=404)
    if request.method == "POST":
        payload = {
            "name": request.POST.get("name"),
            "description": request.POST.get("description", "")
        }
        _post(f"{SVC['product']}/brands/{brand_id}/", json=payload, request=request, method="PUT")
        return redirect("admin_brand_list")
    return render(request, "admin/brand_form.html", {"brand": brand, "role": _role(request)})

# ── Categories ──────────────────────────────────────────────────────────
@require_staff
def admin_category_list(request):
    categories = _list_data(_get(f"{SVC['product']}/categories/", request))
    return render(request, "admin/categories.html", {"categories": categories, "role": _role(request)})

@require_staff
def admin_category_create(request):
    if request.method == "POST":
        payload = {
            "name": request.POST.get("name"),
            "description": request.POST.get("description", "")
        }
        _post(f"{SVC['product']}/categories/", json=payload, request=request)
        return redirect("admin_category_list")
    return render(request, "admin/category_form.html", {"role": _role(request)})

@require_staff
def admin_category_edit(request, category_id):
    category = _get(f"{SVC['product']}/categories/{category_id}/", request)
    if not isinstance(category, dict) or not category.get("id"):
        return render(request, "403.html", {"message": "Không tìm thấy danh mục."}, status=404)
    if request.method == "POST":
        payload = {
            "name": request.POST.get("name"),
            "description": request.POST.get("description", "")
        }
        _post(f"{SVC['product']}/categories/{category_id}/", json=payload, request=request, method="PUT")
        return redirect("admin_category_list")
    return render(request, "admin/category_form.html", {"category": category, "role": _role(request)})

# ── Products ────────────────────────────────────────────────────────────
@require_staff
def admin_product_list(request):
    products = _list_data(_get(f"{SVC['product']}/products/?page_size=100", request))
    return render(request, "admin/products.html", {"products": products, "role": _role(request)})

@require_staff
def admin_product_create(request):
    if request.method == "POST":
        payload = {
            "name": request.POST.get("name"),
            "category_id": int(request.POST.get("category_id")),
            "brand_id": int(request.POST.get("brand_id")) if request.POST.get("brand_id") else None,
            "price": float(request.POST.get("price", 0)),
            "stock": int(request.POST.get("stock", 0)),
            "sku": request.POST.get("sku"),
            "image_url": request.POST.get("image_url", ""),
            "description": request.POST.get("description", "")
        }
        _post(f"{SVC['product']}/products/", json=payload, request=request)
        return redirect("admin_product_list")
        
    categories = _list_data(_get(f"{SVC['product']}/categories/", request))
    brands = _list_data(_get(f"{SVC['product']}/brands/", request))
    return render(request, "admin/product_form.html", {"categories": categories, "brands": brands, "role": _role(request)})

@require_staff
def admin_product_edit(request, product_id):
    product = _get(f"{SVC['product']}/products/{product_id}/", request)
    if not isinstance(product, dict) or not product.get("id"):
        return render(request, "403.html", {"message": "Không tìm thấy sản phẩm."}, status=404)
    if request.method == "POST":
        payload = {
            "name": request.POST.get("name"),
            "category_id": int(request.POST.get("category_id")),
            "brand_id": int(request.POST.get("brand_id")) if request.POST.get("brand_id") else None,
            "price": float(request.POST.get("price", 0)),
            "stock": int(request.POST.get("stock", 0)),
            "sku": request.POST.get("sku"),
            "image_url": request.POST.get("image_url", ""),
            "description": request.POST.get("description", "")
        }
        _post(f"{SVC['product']}/products/{product_id}/", json=payload, request=request, method="PUT")
        return redirect("admin_product_list")
    categories = _list_data(_get(f"{SVC['product']}/categories/", request))
    brands = _list_data(_get(f"{SVC['product']}/brands/", request))
    return render(request, "admin/product_form.html", {
        "product": product,
        "categories": categories,
        "brands": brands,
        "role": _role(request),
    })

# ── Variants ────────────────────────────────────────────────────────────
@require_staff
def admin_variant_create(request, product_id):
    if request.method == "POST":
        payload = {
            "product": product_id,
            "color": request.POST.get("color"),
            "size": request.POST.get("size"),
            "price_modifier": float(request.POST.get("price_modifier", 0)),
            "stock": int(request.POST.get("stock", 0)),
            "sku": request.POST.get("sku")
        }
        _post(f"{SVC['product']}/variants/", json=payload, request=request)
        return redirect("admin_product_list")
    return redirect("admin_product_list")

# ── Inventory ─────────────────────────────────────────────────────────────
@require_staff
def admin_inventory_list(request):
    transactions = _list_data(_get(f"{SVC['product']}/inventory-transactions/", request))
    # Also fetch products to allow adding new transaction easily
    products = _list_data(_get(f"{SVC['product']}/products/?page_size=200", request))
    
    if request.method == "POST":
        payload = {
            "transaction_type": request.POST.get("transaction_type"),
            "quantity_changed": int(request.POST.get("quantity_changed", 0)),
            "stock_after": int(request.POST.get("stock_after", 0)),
            "reference_id": request.POST.get("reference_id", ""),
            "notes": request.POST.get("notes", "")
        }
        product_id = request.POST.get("product_id")
        variant_id = request.POST.get("variant_id")
        if product_id:
            payload["product"] = int(product_id)
        if variant_id:
            payload["variant"] = int(variant_id)
            
        _post(f"{SVC['product']}/inventory-transactions/", json=payload, request=request)
        return redirect("admin_inventory_list")
        
    return render(request, "admin/inventory.html", {"transactions": transactions, "products": products, "role": _role(request)})

# ── Orders ────────────────────────────────────────────────────────────────
@require_staff
def admin_order_list(request):
    orders = _enrich_orders_with_customer_name(
        request, _list_data(_get(f"{SVC['order']}/orders/", request))
    )
    return render(request, "admin/orders.html", {"orders": orders, "role": _role(request)})

@require_staff
def admin_order_update_status(request, order_id):
    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status:
            _post(f"{SVC['order']}/orders/{order_id}/", json={"status": new_status}, request=request, method="PUT")
    return redirect("admin_order_list")

# ── Customers ─────────────────────────────────────────────────────────────
@require_manager
def admin_customer_list(request):
    customers = _list_data(_get(f"{SVC['user']}/internal/customers/", request))
    return render(request, "admin/customers.html", {"customers": customers, "role": _role(request)})

@require_manager
def admin_customer_detail(request, customer_id):
    customer = _get(f"{SVC['user']}/internal/customers/{customer_id}/", request)
    orders = _enrich_orders_with_customer_name(
        request, _list_data(_get(f"{SVC['order']}/orders/?customer_id={customer_id}", request))
    )
    return render(request, "admin/customer_detail.html", {"customer": customer, "orders": orders, "role": _role(request)})

# ── Tickets ───────────────────────────────────────────────────────────────
@require_staff
def admin_ticket_list(request):
    tickets = _enrich_with_customer_names(
        request, _list_data(_get(f"{SVC['interaction_api']}/tickets/", request))
    )
    return render(request, "admin/tickets.html", {"tickets": tickets, "role": _role(request)})

@require_staff
def admin_ticket_detail(request, ticket_id):
    ticket = _get(f"{SVC['interaction_api']}/tickets/{ticket_id}/", request)
    
    if request.method == "POST":
        new_status = request.POST.get("status")
        reply_message = request.POST.get("message")
        
        # 1. Add reply if provided
        if reply_message:
            reply_payload = {
                "ticket": ticket_id,
                "sender_id": _entity_id(request),
                "is_staff": True,
                "message": reply_message
            }
            _post(f"{SVC['interaction_api']}/ticket-replies/", json=reply_payload, request=request)
            
        # 2. Update status if provided
        if new_status and new_status != ticket.get("status"):
            _post(f"{SVC['interaction_api']}/tickets/{ticket_id}/", json={"status": new_status}, request=request, method="PATCH")
            
        return redirect("admin_ticket_detail", ticket_id=ticket_id)
        
    customer_name = _resolve_customer_display_name(request, ticket.get("customer_id") if isinstance(ticket, dict) else None)
    return render(request, "admin/ticket_detail.html", {
        "ticket": ticket,
        "customer_name": customer_name,
        "role": _role(request),
        "chat_api_url": f"/admin/tickets/{ticket_id}/api/messages/",
    })


@require_staff
def admin_ticket_messages_api(request, ticket_id):
    from django.http import JsonResponse

    ticket = _get(f"{SVC['interaction_api']}/tickets/{ticket_id}/", request)
    if not ticket:
        return JsonResponse({"error": "Not found"}, status=404)

    if request.method == "POST":
        message = _parse_chat_message(request)
        if not message:
            return JsonResponse({"error": "Tin nhắn không được để trống."}, status=400)
        resp = _post_ticket_reply(request, ticket_id, _entity_id(request), True, message)
        if not resp or resp.status_code not in (200, 201):
            return JsonResponse({"error": "Không gửi được tin nhắn."}, status=502)
        if ticket.get("status") == "OPEN":
            _post(
                f"{SVC['interaction_api']}/tickets/{ticket_id}/",
                json={"status": "IN_PROGRESS"},
                request=request,
                method="PATCH",
            )
        ticket = _get(f"{SVC['interaction_api']}/tickets/{ticket_id}/", request, cache_ttl=0)

    return JsonResponse(ticket_chat_payload(ticket))
