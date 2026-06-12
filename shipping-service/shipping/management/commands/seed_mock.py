"""
Seed shipping methods, zones và bản ghi vận chuyển mẫu.
"""
import os
import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from shipping.models import Shipping, ShippingAddress, ShippingMethod, ShippingState, ShippingStatus, ShippingZone


VIETNAM_CITIES = [
    ("Hà Nội", 5), ("Ha Noi", 5), ("Hanoi", 5),
    ("Hồ Chí Minh", 15), ("Ho Chi Minh", 15), ("HCM", 15), ("TP.HCM", 15),
    ("Đà Nẵng", 25), ("Da Nang", 25),
    ("Cần Thơ", 35), ("Can Tho", 35),
    ("Hải Phòng", 20), ("Hai Phong", 20),
    ("Nha Trang", 40), ("Huế", 30), ("Hue", 30),
    ("Vũng Tàu", 22), ("Vung Tau", 22),
    ("Biên Hòa", 18), ("Bien Hoa", 18),
    ("Buôn Ma Thuột", 55), ("Quy Nhon", 48), ("Quy Nhơn", 48),
    ("Thái Nguyên", 28), ("Vinh", 42), ("Long Xuyên", 38),
    ("Rạch Giá", 52), ("Pleiku", 60), ("Đà Lạt", 45), ("Da Lat", 45),
]


class Command(BaseCommand):
    help = "Seed default shipping methods, zones and sample shipments"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true")
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--shipments", type=int, default=int(os.getenv("MOCK_SHIPPING_COUNT", "180")))
        parser.add_argument("--order-max-id", type=int, default=int(os.getenv("MOCK_ORDER_COUNT", "250")))

    def handle(self, *args, **options):
        rng = random.Random(21)
        shipment_target = max(20, int(options["shipments"]))
        order_max = max(20, int(options["order_max_id"]))

        methods_data = [
            {
                "method_name": "Giao hàng tiêu chuẩn",
                "description": "3-5 ngày",
                "estimated_days": 5,
                "rate": 25000,
                "min_weight": 0,
                "max_weight": 10,
                "min_distance": 0,
                "max_distance": 50,
            },
            {
                "method_name": "Giao hàng nhanh",
                "description": "1-2 ngày",
                "estimated_days": 2,
                "rate": 45000,
                "min_weight": 0,
                "max_weight": 5,
                "min_distance": 0,
                "max_distance": 30,
            },
            {
                "method_name": "Giao hàng tiết kiệm",
                "description": "5-7 ngày",
                "estimated_days": 7,
                "rate": 15000,
                "min_weight": 0,
                "max_weight": 20,
                "min_distance": 0,
                "max_distance": 100,
            },
            {
                "method_name": "Giao hàng siêu tốc",
                "description": "Trong ngày (nội thành)",
                "estimated_days": 1,
                "rate": 65000,
                "min_weight": 0,
                "max_weight": 3,
                "min_distance": 0,
                "max_distance": 15,
            },
        ]
        for m in methods_data:
            ShippingMethod.objects.update_or_create(
                method_name=m["method_name"],
                defaults=m,
            )
        self.stdout.write(self.style.SUCCESS(f"Upserted {len(methods_data)} shipping methods."))

        zone_created = 0
        for city_name, distance_km in VIETNAM_CITIES:
            _, was_created = ShippingZone.objects.get_or_create(
                city_name=city_name,
                defaults={"distance_km": distance_km},
            )
            if was_created:
                zone_created += 1
        if zone_created:
            self.stdout.write(self.style.SUCCESS(f"Created {zone_created} shipping zones."))

        if options.get("clear"):
            ShippingStatus.objects.all().delete()
            ShippingAddress.objects.all().delete()
            Shipping.objects.all().delete()
            self.stdout.write(self.style.WARNING("Đã xóa dữ liệu shipping."))

        if Shipping.objects.exists() and not options.get("force"):
            self.stdout.write(self.style.NOTICE(
                f"Đã có {Shipping.objects.count()} shipments, bỏ qua (dùng --force --clear)."
            ))
            return

        methods = list(ShippingMethod.objects.all())
        statuses = [ShippingState.SHIPPED, ShippingState.PROCESSING, ShippingState.PENDING, ShippingState.FAILED]
        cities = [c[0] for c in VIETNAM_CITIES[:12]]
        created = 0

        for order_id in range(1, order_max + 1):
            if Shipping.objects.filter(order_id=order_id).exists():
                continue
            if created >= shipment_target:
                break
            method = rng.choice(methods)
            status = rng.choice(statuses)
            shipping = Shipping.objects.create(
                order_id=order_id,
                tracking_number=f"VN{order_id:08d}{rng.randint(10, 99)}",
                shipping_method=method,
                status=status,
                estimated_delivery_date=date.today() + timedelta(days=method.estimated_days),
            )
            city = rng.choice(cities)
            ShippingAddress.objects.create(
                shipping=shipping,
                recipient_name=f"Khách hàng {rng.randint(1, 50)}",
                address_line=f"{rng.randint(1, 500)} Đường {rng.randint(1, 30)}",
                city=city,
                state="",
                country="Việt Nam",
                postal_code=f"{rng.randint(10000, 99999)}",
                phone=f"09{rng.randint(10000000, 99999999)}",
            )
            ShippingStatus.objects.create(
                shipping=shipping,
                status=status,
                description="Cập nhật trạng thái vận chuyển mẫu.",
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {created} shipping records."))
