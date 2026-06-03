from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from app.services.recommendation_pipeline import RecommendationPipeline

@api_view(['GET'])
@permission_classes([AllowAny])
def get_personal(request):
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        return Response({"error": "X-User-Id header is required"}, status=400)
        
    limit = int(request.GET.get('limit', 10))
    result = RecommendationPipeline.get_personal_recommendations(user_id, limit)
    
    return Response({
        "user_id": user_id,
        "model_version": result.get("model_version"),
        "recommendation_id": result.get("recommendation_id"),
        "recommendations": result.get("recommendations")
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def get_trending(request):
    limit = int(request.GET.get('limit', 10))
    recommendations = RecommendationPipeline.get_trending_recommendations(limit)
    
    return Response({
        "recommendations": recommendations
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def track_feedback(request):
    from app.models import RecommendationFeedback
    
    data = request.data
    try:
        feedback = RecommendationFeedback.objects.create(
            recommendation_id=data['recommendation_id'],
            user_id=data.get('user_id'),
            product_id=data['product_id'],
            model_version_id=data['model_version_id'],
            event_type=data['event_type'], # 'impression', 'clicked', 'purchased'
            revenue_attributed=data.get('revenue_attributed', 0.0)
        )
        return Response({"status": "ok", "feedback_id": str(feedback.id)})
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['POST'])
@permission_classes([AllowAny]) # In reality, protect this!
def rollback_model(request):
    from app.models import ModelVersion
    
    model_ver_str = request.data.get('model_version')
    if not model_ver_str:
        return Response({"error": "model_version required"}, status=400)
        
    try:
        model_name, version = model_ver_str.rsplit('_v', 1)
        target_model = ModelVersion.objects.get(model_name=model_name, version=version)
        
        # Rollback logic
        target_model.status = 'ROLLED_BACK'
        target_model.rollout_percentage = 0
        target_model.save()
        
        # Optionally, activate a fallback model if none are ACTIVE
        if not ModelVersion.objects.filter(model_name=model_name, status='ACTIVE').exists():
            if target_model.rollback_target:
                fallback = ModelVersion.objects.get(id=target_model.rollback_target)
                fallback.status = 'ACTIVE'
                fallback.rollout_percentage = 100
                fallback.save()
                
        return Response({"status": "rolled_back"})
    except Exception as e:
        return Response({"error": str(e)}, status=400)

