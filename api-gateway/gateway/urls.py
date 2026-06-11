from django.urls import path
from . import views
from . import admin_views
from . import staff_views

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    path("login/",          views.login_view,    name="login"),
    path("logout/",         views.logout_view,   name="logout"),
    path("register/",       views.register_view, name="register"),

    # ── Dashboard ──────────────────────────────────────────────────────────────
    path("",                views.home,           name="home"),

    # ── Products ───────────────────────────────────────────────────────────────
    path("products/",                         views.product_list,    name="product_list"),
    path("products/<int:product_id>/",           views.product_detail,  name="product_detail"),
    path("products/<int:product_id>/review/",    views.product_review,  name="product_review"),
    path("products/<int:product_id>/wishlist/",  views.product_wishlist_toggle, name="product_wishlist_toggle"),
    path("products/<int:product_id>/delete/",    views.product_delete,  name="product_delete"),
    path("promotions/",                       views.promotion_list,  name="promotions"),
    path("wishlist/",                         views.wishlist_view,   name="wishlist"),

    # ── Customers (Removed) ──────────────────────────────────────────────────

    # ── Cart ───────────────────────────────────────────────────────────────────
    path("cart/<int:customer_id>/",           views.view_cart,   name="view_cart"),
    path("cart/<int:customer_id>/checkout/",  views.checkout,   name="checkout"),

    # ── Orders ─────────────────────────────────────────────────────────────────
    path("orders/",                              views.order_list,   name="order_list"),
    path("orders/<int:order_id>/",               views.order_detail, name="order_detail"),
    path("orders/<int:order_id>/tracking/",      views.order_tracking, name="order_tracking"),
    path("returns/",                             views.returns_list, name="returns_list"),
    path("returns/<int:order_id>/",            views.return_request, name="return_request"),
    path("orders/<int:order_id>/pay/",            views.order_pay,   name="order_pay"),
    path("orders/<int:order_id>/pay/callback/",   views.payment_callback, name="payment_callback"),
    path("orders/customer/<int:customer_id>/",   views.customer_orders, name="customer_orders"),
    path("orders/api/status/",                    views.order_status_api, name="order_status_api"),
    path("recommendations/",                      views.recommendation_list, name="recommendations"),

    # ── Catalog ────────────────────────────────────────────────────────────────
    path("catalog/",       views.catalog_view,  name="catalog"),

    # ── AI Chatbot Proxy (no CORS) ─────────────────────────────────────────────
    path("ai/chat/",       views.ai_chat_proxy, name="ai_chat_proxy"),

    # ── Customer Support ───────────────────────────────────────────────────────
    path("support/",                          views.support_list,    name="support_list"),
    path("support/new/",                      views.support_create,  name="support_create"),
    path("support/<str:ticket_id>/",          views.support_detail,  name="support_detail"),

    # ── Staff Portal (Phase 3) ─────────────────────────────────────────────────
    path("staff/dashboard/",                  staff_views.staff_dashboard,       name="staff_dashboard"),
    path("staff/orders/",                     staff_views.staff_order_list,      name="staff_order_list"),
    path("staff/orders/bulk/",                staff_views.staff_order_bulk_update, name="staff_order_bulk_update"),
    path("staff/orders/<int:order_id>/status/", staff_views.staff_order_update_status, name="staff_order_update_status"),
    path("staff/customers/",                  staff_views.staff_customer_list,   name="staff_customer_list"),
    path("staff/customers/<int:customer_id>/", staff_views.staff_customer_detail, name="staff_customer_detail"),
    path("staff/tickets/",                    staff_views.staff_ticket_list,     name="staff_ticket_list"),
    path("staff/tickets/<str:ticket_id>/",    staff_views.staff_ticket_detail,   name="staff_ticket_detail"),

    # ── Profile & Addresses ────────────────────────────────────────────────────
    path("profile/",                          views.profile_view,    name="profile"),
    path("addresses/add/",                    views.address_add,     name="address_add"),
    path("addresses/<int:address_id>/delete/",views.address_delete,  name="address_delete"),
    path("addresses/<int:address_id>/default/",views.address_set_default, name="address_set_default"),

    # ── Admin Portal ───────────────────────────────────────────────────────────
    path("admin/dashboard/",                  admin_views.admin_dashboard, name="admin_dashboard"),
    path("admin/reports/",                    admin_views.admin_reports, name="admin_reports"),
    path("admin/recommendation/",             admin_views.admin_recommendation, name="admin_recommendation"),
    path("admin/products/",                   admin_views.admin_product_list, name="admin_product_list"),
    path("admin/products/create/",            admin_views.admin_product_create, name="admin_product_create"),
    path("admin/categories/",                 admin_views.admin_category_list, name="admin_category_list"),
    path("admin/categories/create/",          admin_views.admin_category_create, name="admin_category_create"),
    path("admin/brands/",                     admin_views.admin_brand_list, name="admin_brand_list"),
    path("admin/brands/create/",              admin_views.admin_brand_create, name="admin_brand_create"),
    path("admin/products/<int:product_id>/variants/create/", admin_views.admin_variant_create, name="admin_variant_create"),
    path("admin/inventory/",                  admin_views.admin_inventory_list, name="admin_inventory_list"),
    path("admin/orders/",                     admin_views.admin_order_list, name="admin_order_list"),
    path("admin/orders/<int:order_id>/status/", admin_views.admin_order_update_status, name="admin_order_update_status"),
    path("admin/customers/",                  admin_views.admin_customer_list, name="admin_customer_list"),
    path("admin/customers/<int:customer_id>/", admin_views.admin_customer_detail, name="admin_customer_detail"),
    path("admin/tickets/",                    admin_views.admin_ticket_list, name="admin_ticket_list"),
    path("admin/tickets/<str:ticket_id>/",    admin_views.admin_ticket_detail, name="admin_ticket_detail"),
]
