from rest_framework.views import APIView
from rest_framework.response import Response
from app.services import RecommenderService

_svc = RecommenderService()


class RecommendationView(APIView):
    """GET /recommendations/<customer_id>/?limit=10"""
    def get(self, request, customer_id):
        limit = int(request.query_params.get("limit", 10))
        book_ids = _svc.recommend(customer_id, limit=limit)
        return Response({"customer_id": customer_id, "recommended_book_ids": book_ids})


class BehaviorEventView(APIView):
    """POST /api/recommender/events/"""
    def post(self, request):
        customer_id = request.data.get("customer_id")
        book_id = request.data.get("book_id")
        action = request.data.get("action")

        try:
            customer_id = int(customer_id)
            book_id = int(book_id)
        except (TypeError, ValueError):
            return Response({"error": "customer_id and book_id must be integers"}, status=400)

        try:
            _svc.track_behavior(customer_id=customer_id, book_id=book_id, action=action)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        return Response({"ok": True}, status=201)
