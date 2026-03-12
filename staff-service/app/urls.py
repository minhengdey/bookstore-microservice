from django.urls import path
from app.views import (
    StaffListCreateView, StaffDetailView,
    StaffLoginView, StaffTokenRefreshView, StaffMeView,
)

urlpatterns = [
    # ── Auth endpoints ────────────────────────────────────────────────────────
    path("auth/login/",   StaffLoginView.as_view()),
    path("auth/refresh/", StaffTokenRefreshView.as_view()),
    path("auth/me/",      StaffMeView.as_view()),

    # ── Staff CRUD ────────────────────────────────────────────────────────────
    path("staff/",          StaffListCreateView.as_view()),
    path("staff/<int:pk>/", StaffDetailView.as_view()),
]
