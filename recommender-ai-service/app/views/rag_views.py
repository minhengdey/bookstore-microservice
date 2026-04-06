"""
rag_views.py
------------
Django REST Framework views cho RAG chatbot endpoint.

POST /api/recommender/chat

v2 — tương thích với RAGPipeline v2 (trả về RAGResponse dataclass).
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from app.services.ai_singleton import AIModelSingleton


def _normalize_chat_history(raw_history, max_turns=12):
    """
    Chuẩn hóa chat_history từ client về format:
    [("user"|"assistant", "message"), ...]
    """
    if not isinstance(raw_history, list):
        return []

    normalized = []
    for item in raw_history:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        role, content = item
        if role not in ("user", "assistant"):
            continue
        if not isinstance(content, str) or not content.strip():
            continue
        normalized.append((role, content.strip()))

    if len(normalized) > max_turns * 2:
        normalized = normalized[-(max_turns * 2):]
    return normalized


class ChatConsultingView(APIView):
    """
    POST /api/recommender/chat

    Request body:
    {
        "query": "Tôi muốn tìm sách về đầu tư tài chính",
        "user_profile": {
            "user_id": 42,
            "age": 30,
            "gender": "male",
            "location": "Hanoi",
            "interests": ["tài chính", "đầu tư"],
            "purchase_ids": [101, 205, 38],
            "browsing_ids": [101, 205, 38, 99]
        }
    }

    Response:
    {
        "query": "...",
        "answer": "...",
        "confidence": 0.82,
        "is_grounded": true,
        "citations": ["Book A", "Book B"],
        "sources": [
            { "service_id": "BOOK001", "service_name": "...",
              "category": "...", "score": 0.91 }
        ]
    }
    """

    def post(self, request):
        data  = request.data
        query = data.get("query", "").strip()

        if not query:
            return Response(
                {"error": "Trường 'query' là bắt buộc."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_profile = data.get("user_profile", None)
        chat_history = _normalize_chat_history(data.get("chat_history"))

        try:
            # ── Lấy singleton pipeline ──────────────────────────────────────
            pipeline = AIModelSingleton.get_pipeline()

            # Đảm bảo history theo từng user request (tránh lẫn context global)
            pipeline.history = chat_history

            # ── DL scores (optional — dùng để re-rank) ─────────────────────
            dl_service_scores = AIModelSingleton.predict_dl_scores(
                user_profile or {}
            )

            # ── Gọi RAG pipeline (v2 — trả về RAGResponse dataclass) ────────
            result = pipeline.chat(
                query             = query,
                user_profile      = user_profile,
                dl_service_scores = dl_service_scores or None,
            )

            # ── Serialize sources ───────────────────────────────────────────
            sources = [
                {
                    "service_id"  : svc.service_id,
                    "service_name": svc.service_name,
                    "category"    : svc.category,
                    "score"       : round(float(svc.score), 4),
                }
                for svc in result.sources
            ]

            return Response(
                {
                    "query"       : result.query,
                    "answer"      : result.answer,
                    "confidence"  : round(float(result.confidence), 3),
                    "is_grounded" : result.is_grounded,
                    "citations"   : result.citations,
                    "sources"     : sources,
                    "chat_history": pipeline.history[-24:],
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": f"AI Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
