from django.urls import path
from app.views.rag_views import KTMPChatConsultingView
from app.views import RecommendationView, BehaviorEventView

urlpatterns = [
    path('api/recommender/chat-ktmp', KTMPChatConsultingView.as_view(), name='rag_chat_ktmp'),
    path("recommendations/<int:customer_id>/", RecommendationView.as_view(), name="recommendations"),
    path("api/recommender/events/", BehaviorEventView.as_view(), name="behavior_events"),
]
