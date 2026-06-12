"""
mock_catalog.py — Sinh dữ liệu catalog lớn (categories, brands, products) cho dev/demo.
"""
from __future__ import annotations

import random
from decimal import Decimal

DEFAULT_PRODUCT_COUNT = 320
DEFAULT_SEED = 42

CATEGORIES = [
    ("Electronics", "Thiết bị điện tử và phụ kiện thông minh", "electronics"),
    ("Home Appliances", "Thiết bị gia dụng cho nhà bếp và sinh hoạt", "home"),
    ("Fashion", "Thời trang, giày dép và phụ kiện", "fashion"),
    ("Beauty & Personal Care", "Chăm sóc cá nhân và làm đẹp", "beauty"),
    ("Sports & Outdoors", "Dụng cụ thể thao và hoạt động ngoài trời", "sports"),
    ("Grocery & Daily Essentials", "Thực phẩm, đồ uống và nhu yếu phẩm", "grocery"),
    ("Books & Stationery", "Sách, văn phòng phẩm và quà tặng", "books"),
    ("Toys & Kids", "Đồ chơi và sản phẩm cho trẻ em", "toys"),
    ("Health & Wellness", "Thực phẩm chức năng và chăm sóc sức khỏe", "health"),
    ("Automotive", "Phụ kiện và chăm sóc xe", "auto"),
    ("Pet Supplies", "Thức ăn và phụ kiện thú cưng", "pet"),
    ("Office & Computing", "Thiết bị văn phòng và phụ kiện máy tính", "office"),
]

CATEGORY_BRANDS: dict[str, list[str]] = {
    "Electronics": ["SoundPulse", "UltraView", "SwiftKeys", "NeoTech", "ZenAudio", "PixelGear"],
    "Home Appliances": ["CleanBot", "CrispAir", "Aroma Brew", "FreshBlend", "HomeMate", "KitchenPro"],
    "Fashion": ["UrbanFlex", "SoftCotton", "CanvasCarry", "LuxeWear", "StreetLine", "ModaVN"],
    "Beauty & Personal Care": ["GlowLab", "IonicCare", "GentleClean", "ColorPop", "SkinGift", "PureGlow"],
    "Sports & Outdoors": ["RunLite", "SteelGo", "FlexMat", "ProKick", "PulseRun", "ActiveZone"],
    "Grocery & Daily Essentials": ["Morning Roast", "NutriOats", "Tokyo Bowl", "DailyBite", "FarmFresh", "GreenPantry"],
    "Books & Stationery": ["BookHouse", "PaperCraft", "InkWell", "StudyPlus", "ReadMore", "NotePro"],
    "Toys & Kids": ["PlayJoy", "KidSmart", "TinyWorld", "FunBox", "HappyKid", "WonderToy"],
    "Health & Wellness": ["VitaLife", "HerbaCare", "NutriMax", "WellBeing", "BioHealth", "CarePlus"],
    "Automotive": ["AutoCare", "DrivePro", "CarShield", "RoadMate", "MotorFit", "SpeedLine"],
    "Pet Supplies": ["PetLove", "PawCare", "HappyPet", "FurFriend", "TailWag", "PetPantry"],
    "Office & Computing": ["DeskPro", "OfficeHub", "TechDesk", "WorkFlow", "PrintMaster", "CableCore"],
}

PRODUCT_LINES: dict[str, list[tuple[str, str, int, int]]] = {
    "Electronics": [
        ("Tai nghe không dây", "HP", 390_000, 4_990_000),
        ("Loa Bluetooth", "SPK", 290_000, 3_200_000),
        ("Bàn phím cơ", "KB", 690_000, 2_800_000),
        ("Chuột gaming", "MS", 190_000, 1_600_000),
        ("Màn hình", "MN", 2_100_000, 8_900_000),
        ("Sạc nhanh", "CH", 120_000, 890_000),
        ("Cáp USB-C", "CB", 49_000, 350_000),
    ],
    "Home Appliances": [
        ("Máy xay sinh tố", "BL", 590_000, 2_400_000),
        ("Nồi chiên không dầu", "AF", 990_000, 3_800_000),
        ("Máy pha cà phê", "CF", 1_200_000, 4_500_000),
        ("Robot hút bụi", "RB", 2_800_000, 9_900_000),
        ("Máy lọc không khí", "AP", 1_500_000, 6_500_000),
        ("Ấm siêu tốc", "KT", 250_000, 1_200_000),
    ],
    "Fashion": [
        ("Áo thun", "TS", 180_000, 890_000),
        ("Áo khoác gió", "JK", 390_000, 1_800_000),
        ("Quần jean", "JN", 320_000, 1_500_000),
        ("Giày sneaker", "SN", 450_000, 2_400_000),
        ("Túi tote", "BG", 220_000, 1_100_000),
        ("Mũ bucket", "HT", 120_000, 450_000),
    ],
    "Beauty & Personal Care": [
        ("Son dưỡng môi", "LP", 89_000, 420_000),
        ("Serum Vitamin C", "SR", 280_000, 1_200_000),
        ("Sữa rửa mặt", "FC", 120_000, 580_000),
        ("Máy sấy tóc", "HD", 690_000, 2_800_000),
        ("Kem chống nắng", "SC", 150_000, 720_000),
        ("Tẩy trang", "RM", 95_000, 390_000),
    ],
    "Sports & Outdoors": [
        ("Giày chạy bộ", "SH", 590_000, 2_800_000),
        ("Thảm yoga", "YG", 280_000, 1_200_000),
        ("Bình giữ nhiệt", "BT", 180_000, 890_000),
        ("Bóng đá", "BL", 150_000, 890_000),
        ("Tạ tay", "DB", 120_000, 1_500_000),
        ("Dây nhảy", "JR", 49_000, 290_000),
    ],
    "Grocery & Daily Essentials": [
        ("Cà phê rang xay", "CF", 89_000, 480_000),
        ("Yến mạch", "OT", 65_000, 320_000),
        ("Mì gói", "RM", 29_000, 180_000),
        ("Bánh quy", "CK", 35_000, 220_000),
        ("Trà túi lọc", "TE", 45_000, 280_000),
        ("Dầu ăn", "OL", 55_000, 350_000),
    ],
    "Books & Stationery": [
        ("Sách kỹ năng", "BK", 79_000, 350_000),
        ("Sổ tay A5", "NB", 35_000, 180_000),
        ("Bút gel", "PN", 12_000, 89_000),
        ("Bộ bút màu", "CL", 45_000, 290_000),
        ("Kẹp giấy", "ST", 15_000, 120_000),
    ],
    "Toys & Kids": [
        ("Lego mini", "LG", 120_000, 890_000),
        ("Gấu bông", "PL", 89_000, 650_000),
        ("Xe đồ chơi", "CR", 150_000, 1_200_000),
        ("Tranh tô màu", "AR", 35_000, 220_000),
        ("Đồ chơi giáo dục", "ED", 180_000, 1_500_000),
    ],
    "Health & Wellness": [
        ("Vitamin tổng hợp", "VT", 180_000, 890_000),
        ("Omega-3", "OM", 220_000, 1_200_000),
        ("Collagen", "CO", 290_000, 1_800_000),
        ("Dụng cụ massage", "MG", 150_000, 1_500_000),
        ("Máy đo huyết áp", "BP", 390_000, 2_400_000),
    ],
    "Automotive": [
        ("Nước hoa xe", "AC", 89_000, 450_000),
        ("Camera hành trình", "DC", 890_000, 4_500_000),
        ("Lót ghế ô tô", "CS", 290_000, 1_800_000),
        ("Bơm lốp mini", "PM", 350_000, 1_500_000),
        ("Cáp kích bình", "JB", 180_000, 890_000),
    ],
    "Pet Supplies": [
        ("Thức ăn hạt chó", "FD", 120_000, 890_000),
        ("Cát vệ sinh mèo", "CT", 89_000, 450_000),
        ("Đồ chơi xương", "TY", 35_000, 290_000),
        ("Vòng cổ LED", "CL", 45_000, 350_000),
        ("Lược chải lông", "BR", 29_000, 180_000),
    ],
    "Office & Computing": [
        ("Ghế công thái học", "CH", 1_200_000, 6_500_000),
        ("Bàn nâng hạ", "DK", 2_400_000, 9_900_000),
        ("Webcam HD", "WC", 390_000, 2_200_000),
        ("Hub USB", "HB", 180_000, 890_000),
        ("Đế laptop", "ST", 120_000, 650_000),
    ],
}

DESCRIPTIONS = [
    "Sản phẩm chất lượng, phù hợp nhu cầu hàng ngày và dễ sử dụng.",
    "Thiết kế gọn nhẹ, tiện mang theo, phù hợp gia đình và văn phòng.",
    "Chất lượng ổn định, giá hợp lý, được nhiều khách hàng tin dùng.",
    "Lựa chọn phổ biến cho mua sắm online, giao hàng nhanh toàn quốc.",
    "Phù hợp làm quà tặng hoặc sử dụng cá nhân lâu dài.",
]


def _vnd_price(rng: random.Random, low: int, high: int) -> Decimal:
    raw = rng.randint(low // 1000, max(low // 1000, high // 1000)) * 1000
    return Decimal(str(raw))


def generate_brands() -> list[dict]:
    brands = []
    seen = set()
    for cat_name, _desc, _slug in CATEGORIES:
        for brand in CATEGORY_BRANDS.get(cat_name, ["Generic"]):
            key = brand.lower()
            if key in seen:
                continue
            seen.add(key)
            brands.append({
                "name": brand,
                "description": f"Thương hiệu {brand} — {cat_name}",
            })
    return brands


def generate_products(target_count: int = DEFAULT_PRODUCT_COUNT, seed: int = DEFAULT_SEED) -> list[dict]:
    rng = random.Random(seed)
    products: list[dict] = []
    per_category = max(1, (target_count + len(CATEGORIES) - 1) // len(CATEGORIES))
    sku_seen: set[str] = set()

    for cat_name, cat_desc, image_slug in CATEGORIES:
        lines = PRODUCT_LINES.get(cat_name, [("Sản phẩm", "PR", 50_000, 500_000)])
        brands = CATEGORY_BRANDS.get(cat_name, ["Generic"])
        created_in_cat = 0
        variant = 1

        while created_in_cat < per_category and len(products) < target_count:
            line_name, sku_prefix, low, high = rng.choice(lines)
            brand = rng.choice(brands)
            series = rng.choice(["Pro", "Plus", "Lite", "Max", "Air", "Mini", "Ultra", "Neo", "X", "S"])
            name = f"{line_name} {brand} {series}"
            if variant > 1:
                name = f"{name} {variant}"

            sku_base = f"{sku_prefix[:3].upper()}-{brand[:3].upper()}-{variant:04d}"
            sku = sku_base
            while sku in sku_seen:
                variant += 1
                sku = f"{sku_prefix[:3].upper()}-{brand[:3].upper()}-{variant:04d}"
            sku_seen.add(sku)

            price = _vnd_price(rng, low, high)
            stock = rng.randint(15, 450)
            products.append({
                "name": name,
                "category_name": cat_name,
                "category_description": cat_desc,
                "brand_name": brand,
                "price": price,
                "sku": sku,
                "image_url": f"/static/product-images/{image_slug}.svg",
                "attributes": {
                    "brand": brand,
                    "category": cat_name,
                    "series": series,
                },
                "description": f"{name}. {rng.choice(DESCRIPTIONS)}",
                "status": "active",
                "stock": stock,
            })
            created_in_cat += 1
            variant += 1

    return products[:target_count]
