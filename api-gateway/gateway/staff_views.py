from django.shortcuts import render, redirect
from django.contrib import messages
from .views import (
    _get, _post, _role, _entity_id, _list_data, _total_count, _fmt_vnd, SVC,
    _enrich_orders_with_customer_name, _enrich_with_customer_names, _resolve_customer_display_name,
    ticket_chat_payload, _parse_chat_message, _post_ticket_reply,
)
from .permissions import require_staff

INTERACTION = SVC["interaction_api"]


@require_staff
def staff_dashboard(request):
    metrics = _get(f"{SVC['order']}/orders/metrics/", request) or {}
    orders_payload = _get(f"{SVC['order']}/orders/", request, cache_ttl=10)
    tickets_payload = _get(f"{INTERACTION}/tickets/", request)
    open_tickets = sum(
        1 for t in _list_data(tickets_payload)
        if t.get("status") in ("OPEN", "IN_PROGRESS")
    )
    status_breakdown = metrics.get("status_breakdown", {})
    return render(request, "staff/dashboard.html", {
        "role": _role(request),
        "metrics": metrics,
        "total_orders": metrics.get("total_orders", _total_count(orders_payload)),
        "total_revenue": _fmt_vnd(metrics.get("total_revenue", 0)),
        "status_breakdown": status_breakdown,
        "open_tickets": open_tickets,
        "pending_orders": status_breakdown.get("PENDING_PAYMENT", 0) + status_breakdown.get("PAID", 0),
    })


@require_staff
def staff_order_list(request):
    orders = _enrich_orders_with_customer_name(
        request, _list_data(_get(f"{SVC['order']}/orders/", request))
    )
    return render(request, "staff/orders.html", {"orders": orders, "role": _role(request)})


@require_staff
def staff_order_update_status(request, order_id):
    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status:
            _post(f"{SVC['order']}/orders/{order_id}/", json={"status": new_status}, request=request, method="PUT")
    return redirect("staff_order_list")


@require_staff
def staff_order_bulk_update(request):
    if request.method == "POST":
        order_ids = [int(x) for x in request.POST.getlist("order_ids") if x.isdigit()]
        action = request.POST.get("action")
        if order_ids and action in ("approve", "cancel"):
            resp = _post(
                f"{SVC['order']}/orders/bulk-update/",
                json={"order_ids": order_ids, "action": action},
                request=request,
            )
            if resp and resp.status_code == 200:
                result = resp.json()
                updated = len(result.get("updated", []))
                failed = len(result.get("failed", []))
                if updated:
                    messages.success(request, f"Đã cập nhật {updated} đơn hàng.")
                if failed:
                    messages.warning(request, f"{failed} đơn hàng không thể cập nhật.")
            else:
                messages.error(request, "Không thể cập nhật đơn hàng. Vui lòng thử lại.")
    return redirect("staff_order_list")


@require_staff
def staff_customer_list(request):
    customers = _list_data(_get(f"{SVC['user']}/internal/customers/", request))
    return render(request, "staff/customers.html", {"customers": customers, "role": _role(request)})


@require_staff
def staff_customer_detail(request, customer_id):
    customer = _get(f"{SVC['user']}/internal/customers/{customer_id}/", request)
    orders = _enrich_orders_with_customer_name(
        request, _list_data(_get(f"{SVC['order']}/orders/?customer_id={customer_id}", request))
    )
    tickets = _enrich_with_customer_names(
        request, _list_data(_get(f"{INTERACTION}/tickets/?customer_id={customer_id}", request))
    )
    return render(request, "staff/customer_detail.html", {
        "customer": customer,
        "orders": orders,
        "tickets": tickets,
        "role": _role(request),
    })


@require_staff
def staff_ticket_list(request):
    tickets = _enrich_with_customer_names(
        request, _list_data(_get(f"{INTERACTION}/tickets/", request))
    )
    return render(request, "staff/tickets.html", {"tickets": tickets, "role": _role(request)})


@require_staff
def staff_ticket_detail(request, ticket_id):
    ticket = _get(f"{INTERACTION}/tickets/{ticket_id}/", request)

    if request.method == "POST":
        new_status = request.POST.get("status")
        reply_message = request.POST.get("message")

        if reply_message:
            reply_payload = {
                "ticket": ticket_id,
                "sender_id": _entity_id(request),
                "is_staff": True,
                "message": reply_message,
            }
            _post(f"{INTERACTION}/ticket-replies/", json=reply_payload, request=request)

        if new_status and new_status != ticket.get("status"):
            _post(f"{INTERACTION}/tickets/{ticket_id}/", json={"status": new_status}, request=request, method="PATCH")

        return redirect("staff_ticket_detail", ticket_id=ticket_id)

    customer_name = _resolve_customer_display_name(
        request, ticket.get("customer_id") if isinstance(ticket, dict) else None
    )
    return render(request, "staff/ticket_detail.html", {
        "ticket": ticket,
        "customer_name": customer_name,
        "role": _role(request),
        "chat_api_url": f"/staff/tickets/{ticket_id}/api/messages/",
    })


@require_staff
def staff_ticket_messages_api(request, ticket_id):
    from django.http import JsonResponse

    ticket = _get(f"{INTERACTION}/tickets/{ticket_id}/", request)
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
                f"{INTERACTION}/tickets/{ticket_id}/",
                json={"status": "IN_PROGRESS"},
                request=request,
                method="PATCH",
            )
        ticket = _get(f"{INTERACTION}/tickets/{ticket_id}/", request, cache_ttl=0)

    return JsonResponse(ticket_chat_payload(ticket))
