import re
import threading
from pathlib import Path

from django.core.management import call_command
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from common.auth import require_staff_fn, require_manager_fn
from app.models import ModelVersion, ModelMetric


def _parse_evaluation_file():
    """Đọc metrics Accuracy/F1 từ file đánh giá offline."""
    eval_path = Path(__file__).resolve().parents[2] / "models" / "model_best_evaluation.txt"
    if not eval_path.exists():
        return {"models": [], "best_model": None, "raw": ""}

    raw = eval_path.read_text(encoding="utf-8", errors="replace")
    models = []
    for line in raw.splitlines():
        m = re.match(
            r"\s*(GRU|LSTM|BiLSTM)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)",
            line,
        )
        if m:
            name, acc, f1_macro, f1_weighted, epochs = m.groups()
            models.append({
                "name": name,
                "accuracy": float(acc),
                "f1_macro": float(f1_macro),
                "f1_weighted": float(f1_weighted),
                "epochs": int(epochs),
            })

    best = next((m for m in models if "BiLSTM" in m["name"]), models[0] if models else None)
    return {"models": models, "best_model": best, "raw": raw}


@api_view(["GET"])
@require_staff_fn
def list_models(request):
    versions = ModelVersion.objects.prefetch_related("metrics").order_by("-created_at")
    data = []
    for mv in versions:
        latest_metric = mv.metrics.order_by("-evaluated_at").first()
        data.append({
            "id": str(mv.id),
            "model_name": mv.model_name,
            "version": mv.version,
            "model_type": mv.model_type,
            "framework": mv.framework,
            "status": mv.status,
            "metric_name": mv.metric_name,
            "metric_value": mv.metric_value,
            "rollout_percentage": mv.rollout_percentage,
            "deployed_at": mv.deployed_at.isoformat() if mv.deployed_at else None,
            "created_at": mv.created_at.isoformat() if mv.created_at else None,
            "ctr": latest_metric.ctr if latest_metric else None,
            "ndcg": latest_metric.ndcg if latest_metric else None,
        })
    evaluation = _parse_evaluation_file()
    return Response({"versions": data, "offline_evaluation": evaluation})


@api_view(["GET"])
@require_staff_fn
def model_evaluation(request):
    return Response(_parse_evaluation_file())


_retrain_running = False


@api_view(["POST"])
@require_manager_fn
def trigger_retrain(request):
    global _retrain_running
    if _retrain_running:
        return Response({"status": "already_running"}, status=status.HTTP_409_CONFLICT)

    model_type = request.data.get("model_type", "IMPLICIT_CF")

    def _run():
        global _retrain_running
        try:
            if model_type == "IMPLICIT_CF":
                call_command("train_implicit_cf_local")
            else:
                call_command("train_implicit_cf_local")
        finally:
            _retrain_running = False

    _retrain_running = True
    threading.Thread(target=_run, daemon=True).start()
    return Response({"status": "started", "model_type": model_type})


@api_view(["POST"])
@require_manager_fn
def activate_model(request):
    model_id = request.data.get("model_id")
    if not model_id:
        return Response({"error": "model_id required"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        target = ModelVersion.objects.get(pk=model_id)
    except ModelVersion.DoesNotExist:
        return Response({"error": "Model not found"}, status=status.HTTP_404_NOT_FOUND)

    ModelVersion.objects.filter(model_name=target.model_name, status="ACTIVE").update(
        status="DEPRECATED", rollout_percentage=0
    )
    target.status = "ACTIVE"
    target.rollout_percentage = 100
    target.save(update_fields=["status", "rollout_percentage"])
    return Response({"status": "activated", "model_id": str(target.id)})


@api_view(["GET"])
@require_staff_fn
def retrain_status(request):
    return Response({"running": _retrain_running})
