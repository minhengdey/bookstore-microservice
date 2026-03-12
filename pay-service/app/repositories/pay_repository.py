from app.models import Payment, PaymentMethod, Refund, Transaction, CustomerPaymentMethod


class PaymentMethodRepository:
    def get_all(self): return PaymentMethod.objects.filter(is_active=True)
    def get_by_id(self, pk): return PaymentMethod.objects.filter(pk=pk).first()
    def create(self, **kw): return PaymentMethod.objects.create(**kw)


class PaymentRepository:
    def get_all(self): return Payment.objects.select_related("payment_method").all()
    def get_by_id(self, pk): return Payment.objects.select_related("payment_method").filter(pk=pk).first()
    def get_by_order(self, order_id): return Payment.objects.filter(order_id=order_id).first()
    def create(self, **kw): return Payment.objects.create(**kw)
    def update_status(self, payment, status):
        payment.payment_status = status; payment.save(update_fields=["payment_status"]); return payment
    def create_refund(self, payment, **kw):
        refund = Refund.objects.create(payment=payment, **kw)
        Transaction.objects.create(
            order_id=payment.order_id, refund_id=refund.id,
            transaction_type="refund", value=kw.get("refund_amount", 0),
        )
        return refund
    def create_transaction(self, **kw): return Transaction.objects.create(**kw)
