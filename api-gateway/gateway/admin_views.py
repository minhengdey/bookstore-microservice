from django.shortcuts import render, redirect
from django.contrib import messages
from .views import _get, _post, _delete, _role, _entity_id, _total_count, _list_data, _fmt_vnd, SVC
from .permissions import require_staff, require_manager

INTERACTION = SVC["interaction_api"]

# ── Dashboard & Reports (Phase 4) ─────────────────────────────────────────
@require_manager
def admin_dashboard(request):
    metrics = _get(f"{SVC['order']}/orders/metrics/", request) or {}
    products_payload = _get(f"{SVC['product']}/products/", request, cache_ttl=30)
    customers = _list_data(_get(f"{SVC['user']}/internal/customers/", request))
    orders_payload = _get(f"{SVC['order']}/orders/", request, cache_ttl=10)
    status_breakdown = metrics.get("status_breakdown", {})
    return render(request, "admin/dashboard.html", {
        "role": _role(request),
        "total_products": _total_count(products_payload),
        "total_customers": len(customers),
        "total_orders": metrics.get("total_orders", _total_count(orders_payload)),
        "total_revenue": _fmt_vnd(metrics.get("total_revenue", 0)),
        "status_breakdown": status_breakdown,
        "delivered_orders": status_breakdown.get("DELIVERED", 0),
        "cancelled_orders": status_breakdown.get("CANCELLED", 0),
        "pending_revenue_orders": status_breakdown.get("PENDING_PAYMENT", 0) + status_breakdown.get("PAID", 0),
    })


@require_manager
def admin_reports(request):
    metrics = _get(f"{SVC['order']}/orders/metrics/", request) or {}
    orders = _list_data(_get(f"{SVC['order']}/orders/", request))
    products = _list_data(_get(f"{SVC['product']}/products/?page_size=200", request))
    promotions = _list_data(_get(f"{SVC['promotion']}/api/promotions/", request))

    product_sales = {}
    for order in orders:
        if order.get("status") not in ("DELIVERED", "PAID", "PROCESSING", "SHIPPING"):
            continue
        for item in order.get("items", []):
            pid = item.get("product_id")
            if pid:
                product_sales[pid] = product_sales.get(pid, 0) + int(item.get("quantity", 0))

    top_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:10]
    product_map = {p["id"]: p.get("name", f"SP #{p['id']}") for p in products}
    top_sellers = [
        {"id": pid, "name": product_map.get(pid, f"Sản phẩm #{pid}"), "qty": qty}
        for pid, qty in top_products
    ]

    status_breakdown = metrics.get("status_breakdown", {})
    return render(request, "admin/reports.html", {
        "role": _role(request),
        "metrics": metrics,
        "total_revenue": _fmt_vnd(metrics.get("total_revenue", 0)),
        "status_breakdown": status_breakdown,
        "top_sellers": top_sellers,
        "promotion_count": len(promotions),
        "total_orders": metrics.get("total_orders", len(orders)),
    })


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
    orders = _list_data(_get(f"{SVC['order']}/orders/", request))
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
    orders = _list_data(_get(f"{SVC['order']}/orders/?customer_id={customer_id}", request))
    return render(request, "admin/customer_detail.html", {"customer": customer, "orders": orders, "role": _role(request)})

# ── Tickets ───────────────────────────────────────────────────────────────
@require_staff
def admin_ticket_list(request):
    tickets = _list_data(_get(f"{SVC['interaction_api']}/tickets/", request))
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
        
    return render(request, "admin/ticket_detail.html", {"ticket": ticket, "role": _role(request)})
