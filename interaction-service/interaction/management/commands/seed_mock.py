"""
Seed reviews, wishlist, tickets mẫu.
"""
import os
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from interaction.models.review import Review
from interaction.models.wishlist import Wishlist
from interaction.models.ticket import Ticket


class Command(BaseCommand):
    help = "Seed interaction mock data (reviews, wishlists, tickets)"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true")
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--reviews", type=int, default=int(os.getenv("MOCK_REVIEW_COUNT", "600")))
        parser.add_argument("--wishlists", type=int, default=int(os.getenv("MOCK_WISHLIST_COUNT", "400")))
        parser.add_argument("--tickets", type=int, default=int(os.getenv("MOCK_TICKET_COUNT", "80")))
        parser.add_argument("--customers", type=int, default=int(os.getenv("MOCK_CUSTOMER_COUNT", "50")))
        parser.add_argument("--product-max-id", type=int, default=int(os.getenv("MOCK_PRODUCT_COUNT", "320")))

    def handle(self, *args, **options):
        rng = random.Random(99)
        customers = max(3, int(options["customers"]))
        product_max = max(24, int(options["product_max_id"]))

        if options.get("clear"):
            Review.objects.all().delete()
            Wishlist.objects.all().delete()
            Ticket.objects.all().delete()
            self.stdout.write(self.style.WARNING("Đã xóa dữ liệu interaction."))

        if Review.objects.exists() and not options.get("force"):
            self.stdout.write(self.style.NOTICE("Interaction data exists, bỏ qua (dùng --force --clear)."))
            return

        comments = [
            "Sản phẩm ổn, giao hàng nhanh.",
            "Đúng mô tả, mình sẽ mua lại.",
            "Giá hợp lý, chất lượng khá.",
            "Bao bì cẩn thận, hài lòng.",
            "Dùng được, phù hợp nhu cầu.",
            "Hơi chậm ship nhưng sản phẩm ok.",
        ]

        review_rows = []
        seen_review = set()
        for _ in range(int(options["reviews"])):
            cid = rng.randint(1, customers)
            pid = rng.randint(1, product_max)
            key = (cid, pid)
            if key in seen_review:
                continue
            seen_review.add(key)
            review_rows.append(Review(
                customer_id=cid,
                product_id=pid,
                rating=rng.randint(3, 5),
                comment_text=rng.choice(comments),
                verified_purchase=rng.random() < 0.6,
            ))
        Review.objects.bulk_create(review_rows, batch_size=500)

        wish_rows = []
        seen_wish = set()
        for _ in range(int(options["wishlists"])):
            cid = rng.randint(1, customers)
            pid = rng.randint(1, product_max)
            key = (cid, pid)
            if key in seen_wish:
                continue
            seen_wish.add(key)
            wish_rows.append(Wishlist(customer_id=cid, product_id=pid))
        Wishlist.objects.bulk_create(wish_rows, batch_size=500)

        statuses = ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]
        ticket_rows = []
        for i in range(int(options["tickets"])):
            cid = rng.randint(1, customers)
            ticket_rows.append(Ticket(
                customer_id=cid,
                order_id=rng.randint(1, 250) if rng.random() < 0.7 else None,
                subject=rng.choice([
                    "Hỏi về thời gian giao hàng",
                    "Sản phẩm bị lỗi",
                    "Yêu cầu đổi size",
                    "Hỏi khuyến mãi",
                    "Không nhận được email xác nhận",
                ]),
                content="Khách hàng cần hỗ trợ đơn hàng / sản phẩm.",
                status=rng.choice(statuses),
            ))
        Ticket.objects.bulk_create(ticket_rows, batch_size=200)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(review_rows)} reviews, {len(wish_rows)} wishlists, {len(ticket_rows)} tickets."
        ))
