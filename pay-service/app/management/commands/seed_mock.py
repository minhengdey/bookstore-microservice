"""
Tạo dữ liệu mẫu: PaymentMethod, Payment, Transaction, CustomerPaymentMethod, Refund.
Giả định order-service đã seed (order_id 1, 2).
Chạy: python manage.py seed_mock
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from app.models import PaymentMethod, Payment, Transaction, CustomerPaymentMethod, Refund
from app.models.payment import PaymentStatus


class Command(BaseCommand):
    help = "Seed mock data: payment methods, payments, transactions"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Xóa dữ liệu cũ trước khi seed")

    def handle(self, *args, **options):
        if options.get("clear"):
            Refund.objects.all().delete()
            Transaction.objects.all().delete()
            CustomerPaymentMethod.objects.all().delete()
            Payment.objects.all().delete()
            PaymentMethod.objects.all().delete()
            self.stdout.write(self.style.WARNING("Đã xóa dữ liệu pay."))

        if PaymentMethod.objects.exists():
            self.stdout.write(self.style.NOTICE("Đã có dữ liệu pay, bỏ qua seed."))
            return

        PaymentMethod.objects.create(method_name="Tiền mặt", description="Thanh toán khi nhận hàng", is_active=True)
        PaymentMethod.objects.create(method_name="Chuyển khoản", description="Chuyển khoản ngân hàng", is_active=True)
        PaymentMethod.objects.create(method_name="Ví điện tử", description="MoMo, ZaloPay, VNPay", is_active=True)

        pm1 = PaymentMethod.objects.get(method_name="Chuyển khoản")
        pay1 = Payment.objects.create(
            order_id=1,
            payment_amount=Decimal("150800"),
            payment_method=pm1,
            payment_status=PaymentStatus.COMPLETED,
            transaction_ref="TXN001",
            admin_id=1,
        )
        Transaction.objects.create(
            order_id=1,
            transaction_type="payment",
            value=pay1.payment_amount,
            status="success",
        )

        pay2 = Payment.objects.create(
            order_id=2,
            payment_amount=Decimal("83000"),
            payment_method=pm1,
            payment_status=PaymentStatus.COMPLETED,
            transaction_ref="TXN002",
        )
        Transaction.objects.create(order_id=2, transaction_type="payment", value=pay2.payment_amount, status="success")

        for cid in [1, 2]:
            CustomerPaymentMethod.objects.create(
                customer_id=cid,
                payment_method=pm1,
                account_number="***1234",
                is_default=(cid == 1),
                is_active=True,
            )

        self.stdout.write(self.style.SUCCESS("Created payment methods, 2 payments, transactions, customer payment methods."))
