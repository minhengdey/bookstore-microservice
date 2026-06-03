from django.urls import path
from app.views.rag_views import KTMPChatConsultingView
from app.views import RecommendationView, BehaviorEventView, RecommendAliasView, NextActionPredictionView
from app.views.api import get_personal, get_trending, track_feedback, rollback_model

urlpatterns = [
    path('api/recommender/chat-ktmp', KTMPChatConsultingView.as_view(), name='rag_chat_ktmp'),
    path("recommendations/<int:customer_id>/", RecommendationView.as_view(), name="recommendations"),
    path("api/recommender/next-action/<int:customer_id>/", NextActionPredictionView.as_view(), name="next_action_prediction"),
    path("api/recommender/events/", BehaviorEventView.as_view(), name="behavior_events"),
    
    # Personal and Trending endpoints
    path('api/v1/recommendations/personal', get_personal, name='get_personal'),
    path('api/v1/recommendations/trending', get_trending, name='get_trending'),
    
    # MLOps endpoints
    path('api/v1/recommendations/feedback', track_feedback, name='track_feedback'),
    path('api/v1/models/rollback', rollback_model, name='rollback_model'),
    
    # Alias endpoints to match spec
    path("recommend/", RecommendAliasView.as_view(), name="recommend_alias"),
    path("chatbot/", KTMPChatConsultingView.as_view(), name="chatbot_alias"),
]
