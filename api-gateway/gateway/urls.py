from django.urls import path
from . import views

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
    path("products/<int:product_id>/delete/",    views.product_delete,  name="product_delete"),

    # ── Customers (Removed) ──────────────────────────────────────────────────

    # ── Cart ───────────────────────────────────────────────────────────────────
    path("cart/<int:customer_id>/",           views.view_cart,   name="view_cart"),
    path("cart/<int:customer_id>/checkout/",  views.checkout,   name="checkout"),

    # ── Orders ─────────────────────────────────────────────────────────────────
    path("orders/",                              views.order_list,   name="order_list"),
    path("orders/<int:order_id>/pay/",            views.order_pay,   name="order_pay"),
    path("orders/customer/<int:customer_id>/",   views.customer_orders, name="customer_orders"),
    path("recommendations/",                      views.recommendation_list, name="recommendations"),

    # ── Catalog ────────────────────────────────────────────────────────────────
    path("catalog/",       views.catalog_view,  name="catalog"),

    # ── AI Chatbot Proxy (no CORS) ─────────────────────────────────────────────
    path("ai/chat/",       views.ai_chat_proxy, name="ai_chat_proxy"),
]
