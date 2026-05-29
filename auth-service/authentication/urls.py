from django.urls import path
from .views import LoginView, MeView, RefreshView, RegisterView, LiveHealthView, ReadyHealthView, IntrospectTokenView

urlpatterns = [
    path("auth/register/", RegisterView.as_view()),
    path("auth/login/", LoginView.as_view()),
    path("auth/refresh/", RefreshView.as_view()),
    path("auth/introspect/", IntrospectTokenView.as_view()),
    path("users/me/", MeView.as_view()),
    path("health/live/", LiveHealthView.as_view()),
    path("health/ready/", ReadyHealthView.as_view()),
]
