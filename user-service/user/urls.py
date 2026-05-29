from django.urls import path
from .views import UserProfileView, PublicUserProfileView

urlpatterns = [
    path("internal/users/", UserProfileView.as_view(), name="internal-users"),
    path("internal/users/<int:user_id>/", UserProfileView.as_view(), name="internal-user-profile"),
    path("api/users/me/", UserProfileView.as_view(), name="user-profile-legacy"),
    path("users/me/", PublicUserProfileView.as_view(), name="user-profile-public"),
]
