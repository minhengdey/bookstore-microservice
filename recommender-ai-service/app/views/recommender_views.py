from rest_framework.views import APIView
from rest_framework.response import Response
from app.services import RecommenderService

_svc = RecommenderService()


class RecommendationView(APIView):
    """GET /recommendations/<customer_id>/?limit=10"""
    def get(self, request, customer_id):
        raw_limit = request.query_params.get("limit", "10")
        limit = 0 if str(raw_limit).strip() in {"", "0", "all"} else int(raw_limit)
        payload = _svc.recommend_with_prediction(customer_id, limit=limit)
        return Response(payload)

class RecommendAliasView(APIView):
    """GET /recommend?user_id=123&limit=10"""
    def get(self, request):
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"error": "user_id is required"}, status=400)
        try:
            customer_id = int(user_id)
        except ValueError:
            return Response({"error": "user_id must be an integer"}, status=400)
        raw_limit = request.query_params.get("limit", "10")
        limit = 0 if str(raw_limit).strip() in {"", "0", "all"} else int(raw_limit)
        payload = _svc.recommend_with_prediction(customer_id, limit=limit)
        return Response(payload)


class NextActionPredictionView(APIView):
    """GET /api/recommender/next-action/<customer_id>/"""
    def get(self, request, customer_id):
        prediction = _svc.predict_next_action(customer_id)
        if prediction is None:
            return Response({"customer_id": customer_id, "prediction": None}, status=404)
        return Response({"customer_id": customer_id, "prediction": prediction})


class BehaviorEventView(APIView):
    """POST /api/recommender/events/"""
    def post(self, request):
        customer_id = request.data.get("customer_id")
        product_id = request.data.get("product_id")
        action = request.data.get("action")
        session_id = request.data.get("session_id")
        device = request.data.get("device")
        persona = request.data.get("persona")

        try:
            customer_id = int(customer_id)
            product_id = int(product_id)
        except (TypeError, ValueError):
            return Response({"error": "customer_id and product_id must be integers"}, status=400)

        try:
            _svc.track_behavior(
                customer_id=customer_id,
                product_id=product_id,
                action=action,
                session_id=session_id,
                device=device,
                persona=persona,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        return Response({"ok": True}, status=201)
