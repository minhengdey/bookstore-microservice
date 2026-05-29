import uuid
import logging
from django.db import transaction
from .models import Payment, PaymentMethod, Transaction, Refund
from common.client import InternalClient

logger = logging.getLogger(__name__)

SHIP_SERVICE_URL = "http://shipping-service:8000"

class PaymentMethodService:
    def list(self): return PaymentMethod.objects.all()
    def get(self, pk):
        m = PaymentMethod.objects.filter(pk=pk).first()
        if not m: raise ValueError(f"PaymentMethod {pk} not found")
        return m
    def create(self, data): return PaymentMethod.objects.create(**data)

class PaymentService:
    def __init__(self):
        self.client = InternalClient()

    def list(self): return Payment.objects.select_related('payment_method').prefetch_related('refunds').all()

    def get(self, pk):
        p = Payment.objects.select_related('payment_method').prefetch_related('refunds').filter(pk=pk).first()
        if not p: raise ValueError(f"Payment {pk} not found")
        return p

    def process_payment(self, order_id: int, amount: float, method_id: int = None):
        import time
        start_time = time.time()
        
        with transaction.atomic():
            payment, created = Payment.objects.get_or_create(
                order_id=order_id,
                defaults={
                    "payment_amount": amount,
                    "payment_status": "pending",
                }
            )
            
            if payment.payment_status == "completed":
                # Idempotency: Return existing completed payment
                latency_ms = int((time.time() - start_time) * 1000)
                logger.info("metric_payment_latency", extra={"latency_ms": latency_ms, "order_id": order_id, "idempotent": True})
                return payment

            method = None
            if method_id:
                method = PaymentMethod.objects.filter(pk=method_id).first()
            if not method:
                method = PaymentMethod.objects.first()

            payment.payment_method = method
            payment.payment_amount = amount

            if method:
                payment.payment_status = "completed"
                payment.transaction_ref = str(uuid.uuid4())[:20]
                tx_status = "success"
            else:
                payment.payment_status = "failed"
                tx_status = "failed"

            payment.save()

            Transaction.objects.create(
                order_id=order_id,
                transaction_type="payment",
                value=amount,
                status=tx_status
            )
            
            if payment.payment_status == "completed":
                # Write to Outbox instead of calling shipping-service synchronously
                from .models import PaymentOutbox
                outbox_payload = {
                    "payment_id": payment.id,
                    "order_id": order_id,
                    "amount": str(amount),
                    "shipping_status": "pending"
                }
                PaymentOutbox.objects.create(
                    aggregate_id=str(payment.id),
                    event_type="payment_completed",
                    payload=outbox_payload
                )
            
        latency_ms = int((time.time() - start_time) * 1000)
        logger.info("metric_payment_latency", extra={"latency_ms": latency_ms, "order_id": order_id, "status": payment.payment_status})
                
        return payment

    def refund_payment(self, payment_id: int, amount: float, reason: str = ""):
        with transaction.atomic():
            payment = self.get(payment_id)
            if payment.payment_status != "completed":
                raise ValueError("Can only refund completed payments")
                
            refund = Refund.objects.create(
                payment=payment,
                refund_amount=amount,
                refund_reason=reason
            )
            payment.payment_status = "refunded"
            payment.save(update_fields=["payment_status"])
            
            Transaction.objects.create(
                order_id=payment.order_id,
                transaction_type="refund",
                value=amount,
                status="success"
            )
            return refund
