from django.urls import path
from app.views.rag_views import KTMPChatConsultingView
from app.views import RecommendationView, BehaviorEventView, RecommendAliasView, NextActionPredictionView

urlpatterns = [
    path('api/recommender/chat-ktmp', KTMPChatConsultingView.as_view(), name='rag_chat_ktmp'),
    path("recommendations/<int:customer_id>/", RecommendationView.as_view(), name="recommendations"),
    path("api/recommender/next-action/<int:customer_id>/", NextActionPredictionView.as_view(), name="next_action_prediction"),
    path("api/recommender/events/", BehaviorEventView.as_view(), name="behavior_events"),
    
    # Alias endpoints to match spec
    path("recommend/", RecommendAliasView.as_view(), name="recommend_alias"),
    path("chatbot/", KTMPChatConsultingView.as_view(), name="chatbot_alias"),
]
