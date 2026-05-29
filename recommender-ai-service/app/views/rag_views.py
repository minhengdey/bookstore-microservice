"""
rag_views.py
------------
Django REST Framework views cho RAG chatbot endpoint.

KTMP v1 — tích hợp từ ai-ktmp (Groq + KB_Graph fallback).
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from app.services.ai_singleton import AIModelSingleton


class KTMPChatConsultingView(APIView):
    """
    POST /api/recommender/chat-ktmp
    
    Request body:
    {
        "message": "Hello",
        "user_id": "U001",
        "history": []
    }
    """
    def post(self, request):
        data    = request.data
        message = data.get("message", "")
        user_id = data.get("user_id", "anonymous")
        history = data.get("history", [])
        recent_behaviors = data.get("recent_behaviors", [])

        if not message:
            return Response({"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rag_llm = AIModelSingleton.get_ktmp_rag_llm()
            if rag_llm is None:
                return Response({"answer": "Hệ thống đang khởi động, vui lòng thử lại."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            resp = rag_llm.chat(user_id, message, history=history, recent_behaviors=recent_behaviors)
            return Response({
                "answer":       resp.get("answer", ""),
                "products":     resp.get("products", []),
                "context_used": resp.get("context_used", ""),
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"KTMP AI Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
