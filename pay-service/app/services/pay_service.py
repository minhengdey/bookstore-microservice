import uuid
from app.repositories import PaymentRepository, PaymentMethodRepository


class PaymentMethodService:
    def __init__(self): self.repo = PaymentMethodRepository()
    def list(self): return self.repo.get_all()
    def get(self, pk):
        m = self.repo.get_by_id(pk)
        if not m: raise ValueError(f"PaymentMethod {pk} not found")
        return m
    def create(self, data): return self.repo.create(**data)


class PaymentService:
    def __init__(self):
        self.repo = PaymentRepository()
        self.method_repo = PaymentMethodRepository()

    def list(self): return self.repo.get_all()

    def get(self, pk):
        p = self.repo.get_by_id(pk)
        if not p: raise ValueError(f"Payment {pk} not found")
        return p

    def process_payment(self, order_id: int, amount: float, method_id: int):
        existing = self.repo.get_by_order(order_id)
        if existing and existing.payment_status == "completed":
            raise ValueError("Order already paid")
        method = self.method_repo.get_by_id(method_id)
        if not method:
            raise ValueError(f"PaymentMethod {method_id} not found")
        payment = self.repo.create(
            order_id=order_id, payment_amount=amount,
            payment_method=method, payment_status="completed",
            transaction_ref=str(uuid.uuid4())[:20],
        )
        self.repo.create_transaction(
            order_id=order_id, transaction_type="payment",
            value=amount, status="success",
        )
        return payment

    def refund_payment(self, payment_id: int, amount: float, reason: str = ""):
        payment = self.get(payment_id)
        if payment.payment_status != "completed":
            raise ValueError("Can only refund completed payments")
        refund = self.repo.create_refund(payment, refund_amount=amount, refund_reason=reason)
        self.repo.update_status(payment, "refunded")
        return refund
