from django.urls import path
from app.views.rag_views import ChatConsultingView
from app.views import RecommendationView, BehaviorEventView

urlpatterns = [
    path('api/recommender/chat', ChatConsultingView.as_view(), name='rag_chat'),
    path("recommendations/<int:customer_id>/", RecommendationView.as_view(), name="recommendations"),
    path("api/recommender/events/", BehaviorEventView.as_view(), name="behavior_events"),
]
