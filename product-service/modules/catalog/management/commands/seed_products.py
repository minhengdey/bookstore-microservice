import random
from django.core.management.base import BaseCommand
from modules.catalog.infrastructure.models.product_model import ProductModel, CategoryModel

class Command(BaseCommand):
    help = 'Seed products for Bookstore with diverse categories and AI context'

    def handle(self, *args, **options):
        # 1. Clear existing products to ensure a fresh demo
        ProductModel.objects.all().delete()
        CategoryModel.objects.all().delete()
        self.stdout.write(self.style.WARNING("Cleared existing products and categories..."))

        # 2. Categories
        categories_data = [
            ("Manga & Anime", "Thế giới truyện tranh Nhật Bản siêu hấp dẫn."),
            ("Kỹ năng sống", "Những đầu sách giúp bạn thay đổi tư duy và cuộc đời."),
            ("Công nghệ thông tin", "Cập nhật kiến thức lập trình, AI và phần cứng mới nhất."),
            ("Văn học trẻ", "Truyện ngắn, tản văn và tiểu thuyết cho tuổi teen."),
            ("Kinh doanh - Đầu tư", "Xây dựng tư duy làm giàu và quản trị."),
            ("Thiếu nhi", "Những câu chuyện cổ tích và sách tranh màu sắc."),
            ("Sức khỏe & Tâm lý", "Chăm sóc thân tâm và thấu hiểu bản thân."),
            ("Nấu ăn & Làm đẹp", "Góc dành cho các đầu bếp gia đình và tín đồ làm đẹp."),
            ("Khoa học viễn tưởng", "Khám phá tương lai và những vũ trụ song song."),
            ("Lịch sử - Văn hóa", "Tìm hiểu về cội nguồn và các nền văn minh thế giới.")
        ]

        category_objs = {}
        for name, desc in categories_data:
            cat = CategoryModel.objects.create(name=name, description=desc)
            category_objs[name] = cat

        # 3. Product Patterns for Diversification
        product_patterns = {
            "Manga & Anime": [
                ("One Piece - Tập {i}", "Hành trình tìm kiếm kho báu huyền thoại của Luffy."),
                ("Doraemon - Tuyển tập {i}", "Những bảo bối thần kỳ của chú mèo máy đến từ tương lai."),
                ("Spy x Family {i}", "Gia đình điệp viên đầy hài hước và ấm áp."),
                ("Conan {i}", "Thám tử lừng danh giải mã những vụ án hóc búa.")
            ],
            "Công nghệ thông tin": [
                ("Lập trình Python từ cơ bản đến nâng cao {i}", "Hướng dẫn chi tiết cho người mới bắt đầu học Python."),
                ("Bí mật của trí tuệ nhân tạo {i}", "Khám phá cách AI đang thay đổi thế giới."),
                ("Clean Code: Mã sạch {i}", "Làm sao để viết code dễ hiểu và bảo trì tốt."),
                ("ReactJS Mastery {i}", "Xây dựng ứng dụng web hiện đại với React.")
            ],
            "Kỹ năng sống": [
                ("Đắc nhân tâm {i}", "Nghệ thuật thu phục lòng người trong giao tiếp."),
                ("Nhà giả kim {i}", "Hành trình theo đuổi ước mơ của mỗi con người."),
                ("Khéo ăn khéo nói sẽ có được thiên hạ {i}", "Bí quyết giao tiếp thành công trong mọi tình huống."),
                ("Tuổi trẻ đáng giá bao nhiêu {i}", "Truyền cảm hứng sống hết mình cho giới trẻ.")
            ],
            "Khoa học viễn tưởng": [
                ("Dune: Hành tinh cát {i}", "Sử thi vũ trụ về những cuộc chiến giành quyền lực."),
                ("Người về từ sao hỏa {i}", "Cuộc chiến sinh tồn của một phi hành gia đơn độc."),
                ("Neuromancer {i}", "Khởi nguồn của dòng cyberpunk hiện đại."),
                ("1984 {i}", "Lời cảnh báo về một thế giới bị giám sát hoàn toàn.")
            ]
        }

        # Global list for random assignment
        generic_patterns = [
            ("Sách kiến thức {i}", "Khám phá những kho tàng tri thức mới mẻ."),
            ("Hành trình khám phá {i}", "Những câu chuyện đưa bạn đi khắp thế gian."),
            ("Góc thư giãn cho tâm hồn {i}", "Tản văn nhẹ nhàng cho những ngày bình yên.")
        ]

        # 4. Generate ~100 items
        total_created = 0
        for i in range(1, 101):
            # Select group
            cat_name = random.choice(list(category_objs.keys()))
            cat = category_objs[cat_name]
            
            if cat_name in product_patterns:
                tmpl_name, tmpl_desc = random.choice(product_patterns[cat_name])
            else:
                tmpl_name, tmpl_desc = random.choice(generic_patterns)
            
            name = tmpl_name.format(i=i)
            desc = f"{tmpl_desc.format(i=i)} Một cuốn sách tuyệt vời trong danh mục {cat_name}."
            price = random.randint(50000, 350000)
            
            ProductModel.objects.create(
                name=name,
                category=cat,
                price=price,
                currency='VND',
                sku=f"BOOK-{1000+i}",
                description=desc,
                status='active'
            )
            total_created += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {total_created} books in {len(category_objs)} categories!"))
