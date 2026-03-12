from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.services import PaymentService, PaymentMethodService
from app.serializers import PaymentSerializer, PaymentMethodSerializer, RefundSerializer

_pay_svc = PaymentService()
_method_svc = PaymentMethodService()


class PaymentMethodListView(APIView):
    def get(self, request): return Response(PaymentMethodSerializer(_method_svc.list(), many=True).data)
    def post(self, request):
        try: return Response(PaymentMethodSerializer(_method_svc.create(dict(request.data))).data, status=status.HTTP_201_CREATED)
        except Exception as e: return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PaymentListCreateView(APIView):
    def get(self, request): return Response(PaymentSerializer(_pay_svc.list(), many=True).data)

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
