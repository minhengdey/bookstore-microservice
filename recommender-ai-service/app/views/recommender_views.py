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
