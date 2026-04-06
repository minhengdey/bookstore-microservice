from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.services import PaymentService, PaymentMethodService
from app.serializers import PaymentSerializer, PaymentMethodSerializer, RefundSerializer

_pay_svc = PaymentService()
_method_svc = PaymentMethodService()


def _parse_positive_int(value, default):
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


def _paginate_and_search(request, objs, serializer_cls):
    if hasattr(objs, "order_by"):
        objs = objs.order_by("id")
    else:
        objs = sorted(objs, key=lambda x: getattr(x, "id", 0))
    data = list(serializer_cls(objs, many=True).data)
    keyword = (request.query_params.get("search") or "").strip().lower()
    if keyword:
        data = [
            item for item in data
            if any(keyword in str(value).lower() for value in item.values() if value is not None)
        ]
    page = _parse_positive_int(request.query_params.get("page"), 1)
    page_size = min(_parse_positive_int(request.query_params.get("page_size"), 10), 200)
    total = len(data)
    total_pages = max(1, (total + page_size - 1) // page_size)
    if page > total_pages:
        page = total_pages
    start = (page - 1) * page_size
    end = start + page_size
    next_page = page + 1 if page < total_pages else None
    prev_page = page - 1 if page > 1 else None
    return {
        "count": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "next_page": next_page,
        "prev_page": prev_page,
        "results": data[start:end],
    }


class PaymentMethodListView(APIView):
    def get(self, request): return Response(_paginate_and_search(request, _method_svc.list(), PaymentMethodSerializer))
    def post(self, request):
        try: return Response(PaymentMethodSerializer(_method_svc.create(dict(request.data))).data, status=status.HTTP_201_CREATED)
        except Exception as e: return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PaymentListCreateView(APIView):
    def get(self, request): return Response(_paginate_and_search(request, _pay_svc.list(), PaymentSerializer))

    def post(self, request):
        """POST body: {order_id, payment_amount, payment_method_id}"""
        try:
            payment = _pay_svc.process_payment(
                order_id=int(request.data["order_id"]),
                amount=float(request.data["payment_amount"]),
                method_id=int(request.data["payment_method_id"]),
            )
            return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)
        except (KeyError, ValueError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PaymentDetailView(APIView):
    def get(self, request, pk):
        try: return Response(PaymentSerializer(_pay_svc.get(pk)).data)
        except ValueError as e: return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


class RefundView(APIView):
    def post(self, request, payment_id):
        """POST body: {refund_amount, refund_reason}"""
        try:
            refund = _pay_svc.refund_payment(
                payment_id=payment_id,
                amount=float(request.data.get("refund_amount", 0)),
                reason=request.data.get("refund_reason", ""),
            )
            return Response(RefundSerializer(refund).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
