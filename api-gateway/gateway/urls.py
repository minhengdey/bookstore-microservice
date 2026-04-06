from django.urls import path
from . import views

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    path("login/",          views.login_view,    name="login"),
    path("logout/",         views.logout_view,   name="logout"),
    path("register/",       views.register_view, name="register"),

    # ── Dashboard ──────────────────────────────────────────────────────────────
    path("",                views.home,           name="home"),

    # ── Books ──────────────────────────────────────────────────────────────────
    path("books/",                         views.book_list,    name="book_list"),
    path("books/<int:book_id>/",           views.book_detail,  name="book_detail"),
    path("books/<int:book_id>/delete/",    views.book_delete,  name="book_delete"),

    # ── Customers ──────────────────────────────────────────────────────────────
    path("customers/",     views.customer_list, name="customer_list"),

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
