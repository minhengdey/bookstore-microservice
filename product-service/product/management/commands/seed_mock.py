"""
Tạo dữ liệu mẫu: Category, Product.
Chạy: python manage.py seed_mock
       python manage.py seed_mock --clear   # xóa dữ liệu cũ rồi seed lại
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from product.models import Category, Product, StockReservationLog


CATEGORIES = [
    (1, "Electronics",               "Thiết bị điện tử và phụ kiện thông minh"),
    (2, "Home Appliances",           "Thiết bị gia dụng cho nhà bếp và sinh hoạt"),
    (3, "Fashion",                   "Thời trang, giày dép và phụ kiện"),
    (4, "Beauty & Personal Care",    "Chăm sóc cá nhân và làm đẹp"),
    (5, "Sports & Outdoors",         "Dụng cụ thể thao và hoạt động ngoài trời"),
    (6, "Grocery & Daily Essentials","Thực phẩm, đồ uống và nhu yếu phẩm"),
]

PRODUCTS = [
    # (name, category_id, price, sku, image_url, attributes, description, status, stock)
    ("Tai nghe khử ồn SoundPulse X2", 1, Decimal("1890000"), "ELC-HP-X2",
     "/static/product-images/electronics.svg",
     {"brand": "SoundPulse", "color": "Black", "features": ["Bluetooth 5.3", "Active Noise Cancelling", "30h battery"]},
     "Tai nghe không dây cho nghe nhạc, làm việc và di chuyển hằng ngày.", "active", 120),

    ("Đồng hồ thông minh FitTrack S1", 1, Decimal("2490000"), "ELC-SW-S1",
     "/static/product-images/electronics.svg",
     {"brand": "FitTrack", "color": "Graphite", "features": ["Heart rate", "Sleep tracking", "GPS"]},
     "Đồng hồ theo dõi sức khỏe và luyện tập với màn hình AMOLED.", "active", 80),

    ("Bàn phím cơ SwiftKeys Pro", 1, Decimal("1690000"), "ELC-KB-PRO",
     "/static/product-images/electronics.svg",
     {"brand": "SwiftKeys", "switch": "Brown", "layout": "75%", "connectivity": ["Bluetooth", "2.4GHz", "USB-C"]},
     "Bàn phím cơ đa kết nối cho dân văn phòng và game thủ.", "active", 95),

    ("Màn hình cong UltraView 27Q", 1, Decimal("4890000"), "ELC-MN-27Q",
     "/static/product-images/electronics.svg",
     {"brand": "UltraView", "size": "27 inch", "resolution": "2K", "refresh_rate": "165Hz"},
     "Màn hình cong cho làm việc đa nhiệm và giải trí mượt mà.", "active", 45),

    ("Robot hút bụi CleanBot 3000", 2, Decimal("6990000"), "HOM-RB-3000",
     "/static/product-images/home.svg",
     {"brand": "CleanBot", "suction": "4000Pa", "features": ["Auto mapping", "Wet mop", "App control"]},
     "Robot hút bụi tự động giúp dọn dẹp nhà cửa gọn gàng hơn.", "active", 40),

    ("Nồi chiên không dầu CrispAir 5L", 2, Decimal("2790000"), "HOM-AF-5L",
     "/static/product-images/home.svg",
     {"brand": "CrispAir", "capacity": "5L", "features": ["Rapid air", "Non-stick basket", "8 presets"]},
     "Nồi chiên cho bữa ăn ít dầu mỡ nhưng vẫn giòn ngon.", "active", 70),

    ("Máy pha cà phê Aroma Brew Mini", 2, Decimal("3290000"), "HOM-CF-MINI",
     "/static/product-images/home.svg",
     {"brand": "Aroma Brew", "capacity": "1.2L", "features": ["Auto shut-off", "Keep warm", "Compact design"]},
     "Máy pha cà phê nhỏ gọn cho gia đình và văn phòng.", "active", 55),

    ("Máy xay sinh tố FreshBlend Pro", 2, Decimal("1490000"), "HOM-BL-FPRO",
     "/static/product-images/home.svg",
     {"brand": "FreshBlend", "power": "1000W", "jar": "1.5L", "features": ["Ice crushing", "5 speeds", "Stainless blades"]},
     "Máy xay đa năng cho sinh tố, súp và đồ uống nhanh.", "active", 62),

    ("Áo khoác gió UrbanFlex", 3, Decimal("890000"), "FAS-JK-URB",
     "/static/product-images/fashion.svg",
     {"brand": "UrbanFlex", "size": "L", "material": "Polyester", "gender": "Unisex"},
     "Áo khoác nhẹ, dễ phối đồ cho đi làm và đi chơi.", "active", 110),

    ("Giày chạy bộ RunLite 2.0", 5, Decimal("1450000"), "SPT-SH-RL20",
     "/static/product-images/sports.svg",
     {"brand": "RunLite", "size_range": "39-44", "features": ["Lightweight", "Breathable mesh", "Energy return foam"]},
     "Giày chạy bộ phù hợp tập luyện, đi bộ và marathon ngắn.", "active", 60),

    ("Túi tote CanvasCarry", 3, Decimal("450000"), "FAS-BG-TOTE",
     "/static/product-images/fashion.svg",
     {"brand": "CanvasCarry", "material": "Canvas", "style": "Tote", "features": ["Large capacity", "Minimal design"]},
     "Túi tote canvas tiện dụng cho đi học, đi làm và mua sắm.", "active", 140),

    ("Áo thun basic SoftCotton", 3, Decimal("320000"), "FAS-TS-SCOT",
     "/static/product-images/fashion.svg",
     {"brand": "SoftCotton", "size": "M", "material": "Cotton", "fit": "Regular"},
     "Áo thun basic dễ phối, phù hợp mặc hằng ngày.", "active", 210),

    ("Serum Vitamin C GlowLab", 4, Decimal("520000"), "BTY-SR-CGLOW",
     "/static/product-images/beauty.svg",
     {"brand": "GlowLab", "volume": "30ml", "features": ["Vitamin C", "Niacinamide", "Brightening"]},
     "Serum chăm sóc da hỗ trợ làm sáng và đều màu da.", "active", 150),

    ("Máy sấy tóc IonicCare", 4, Decimal("1290000"), "BTY-HD-ION",
     "/static/product-images/beauty.svg",
     {"brand": "IonicCare", "power": "1800W", "features": ["Ionic care", "3 heat settings", "Foldable handle"]},
     "Máy sấy tóc gọn nhẹ, phù hợp nhu cầu chăm sóc cá nhân tại nhà.", "active", 65),

    ("Sữa rửa mặt GentleClean", 4, Decimal("210000"), "BTY-FC-GENT",
     "/static/product-images/beauty.svg",
     {"brand": "GentleClean", "volume": "150ml", "skin_type": "Sensitive", "features": ["Low pH", "No fragrance"]},
     "Sữa rửa mặt dịu nhẹ cho chu trình chăm sóc da hàng ngày.", "active", 180),

    ("Son dưỡng ColorPop", 4, Decimal("180000"), "BTY-LP-CPOP",
     "/static/product-images/beauty.svg",
     {"brand": "ColorPop", "shade": "Rose", "features": ["Moisturizing", "Shea butter"]},
     "Son dưỡng có màu nhẹ, cấp ẩm và làm mềm môi.", "active", 260),

    ("Bình giữ nhiệt SteelGo 750ml", 5, Decimal("390000"), "SPT-BT-750",
     "/static/product-images/sports.svg",
     {"brand": "SteelGo", "capacity": "750ml", "material": "Stainless steel", "features": ["Vacuum insulation", "Leak proof"]},
     "Bình giữ nhiệt mang đi làm, đi học hoặc tập luyện.", "active", 180),

    ("Thảm yoga FlexMat", 5, Decimal("540000"), "SPT-YG-FLEX",
     "/static/product-images/sports.svg",
     {"brand": "FlexMat", "thickness": "8mm", "material": "TPE", "features": ["Non-slip", "Lightweight"]},
     "Thảm yoga êm, bám sàn tốt cho tập luyện tại nhà.", "active", 95),

    ("Bóng đá training ProKick", 5, Decimal("330000"), "SPT-BL-PKICK",
     "/static/product-images/sports.svg",
     {"brand": "ProKick", "size": "5", "material": "PU", "features": ["Machine stitched", "Outdoor training"]},
     "Bóng đá luyện tập cho sân cỏ nhân tạo và hoạt động thể thao.", "active", 135),

    ("Tai nghe thể thao PulseRun", 5, Decimal("760000"), "SPT-HP-PRUN",
     "/static/product-images/sports.svg",
     {"brand": "PulseRun", "features": ["Sweat resistant", "Ear hooks", "Bluetooth 5.3"]},
     "Tai nghe thể thao ôm tai chắc chắn, phù hợp chạy bộ và tập gym.", "active", 88),

    ("Hạt cà phê rang xay Morning Roast 500g", 6, Decimal("240000"), "GRC-CF-500",
     "/static/product-images/grocery.svg",
     {"brand": "Morning Roast", "weight": "500g", "origin": "Đà Lạt", "roast_level": "Medium"},
     "Hạt cà phê rang xay phục vụ gia đình, văn phòng và quán nhỏ.", "active", 220),

    ("Yến mạch nguyên cám NutriOats", 6, Decimal("160000"), "GRC-OT-NUTO",
     "/static/product-images/grocery.svg",
     {"brand": "NutriOats", "weight": "1kg", "features": ["Whole grain", "High fiber"]},
     "Yến mạch dinh dưỡng cho bữa sáng lành mạnh.", "active", 240),

    ("Mì ramen vị miso Tokyo Bowl", 6, Decimal("99000"), "GRC-RM-TOK",
     "/static/product-images/grocery.svg",
     {"brand": "Tokyo Bowl", "pack": "5 packs", "flavor": "Miso"},
     "Mì ramen ăn liền hương vị Nhật Bản tiện lợi.", "active", 300),

    ("Bánh quy yến mạch DailyBite", 6, Decimal("135000"), "GRC-CK-DBITE",
     "/static/product-images/grocery.svg",
     {"brand": "DailyBite", "weight": "350g", "features": ["Low sugar", "Whole oats"]},
     "Bánh quy giòn nhẹ cho bữa phụ hoặc quà tặng.", "active", 190),
]


class Command(BaseCommand):
    help = "Seed mock data: categories and products"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Xóa dữ liệu cũ trước khi seed")

    def handle(self, *args, **options):
        if options.get("clear"):
            StockReservationLog.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(self.style.WARNING("Đã xóa dữ liệu product."))

        if Product.objects.exists():
            self.stdout.write(self.style.NOTICE("Đã có dữ liệu product, bỏ qua seed."))
            return

        # Seed categories
        cat_map = {}
        for cat_id, name, description in CATEGORIES:
            cat, _ = Category.objects.get_or_create(
                id=cat_id,
                defaults={"name": name, "description": description},
            )
            cat_map[cat_id] = cat

        self.stdout.write(f"  Created {len(cat_map)} categories.")

        # Seed products
        created = 0
        for (name, cat_id, price, sku, image_url, attributes, description, status, stock) in PRODUCTS:
            Product.objects.get_or_create(
                sku=sku,
                defaults={
                    "name": name,
                    "category": cat_map[cat_id],
                    "price": price,
                    "currency": "VND",
                    "image_url": image_url,
                    "attributes": attributes,
                    "description": description,
                    "status": status,
                    "stock": stock,
                },
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(CATEGORIES)} categories and {created} products successfully."
        ))
