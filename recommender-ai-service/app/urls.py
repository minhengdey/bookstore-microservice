from django.urls import path
from app.views import RecommendationView

urlpatterns = [
    path("recommendations/<int:customer_id>/", RecommendationView.as_view()),
]
