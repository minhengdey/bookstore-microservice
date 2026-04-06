"""
Tạo dữ liệu mẫu: Author, Category, Genre, Publisher.
Chạy: python manage.py seed_mock
"""
from django.core.management.base import BaseCommand
from django.db import connection
from app.models import Author, Category, Genre, Publisher


class Command(BaseCommand):
    help = "Seed mock data: authors, categories, genres, publishers"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Xóa dữ liệu cũ trước khi seed")

    def handle(self, *args, **options):
        if options.get("clear"):
            with connection.cursor() as cursor:
                cursor.execute("TRUNCATE TABLE publishers, genres, categories, authors RESTART IDENTITY CASCADE;")
            self.stdout.write(self.style.WARNING("Đã xóa dữ liệu catalog."))

        if Author.objects.exists():
            self.stdout.write(self.style.NOTICE("Đã có dữ liệu catalog, bỏ qua seed."))
            return

        authors = [
            {"author_name": "Nguyễn Nhật Ánh", "biography": "Nhà văn Việt Nam nổi tiếng với truyện thiếu nhi và thanh xuân.", "birth_year": 1955},
            {"author_name": "Nguyễn Ngọc Tư", "biography": "Nhà văn với lối viết mộc mạc, đậm chất miền Tây Nam Bộ.", "birth_year": 1976},
            {"author_name": "Phan Việt", "biography": "Tác giả viết tản văn và tiểu thuyết về hành trình trưởng thành.", "birth_year": 1978},
            {"author_name": "Gào", "biography": "Tác giả trẻ với nhiều tác phẩm gần gũi đời sống giới trẻ.", "birth_year": 1988},
            {"author_name": "Trang Hạ", "biography": "Dịch giả, nhà văn với nhiều đầu sách được bạn đọc yêu thích.", "birth_year": 1975},
            {"author_name": "Tô Hoài", "biography": "Nhà văn lớn của văn học Việt Nam hiện đại.", "birth_year": 1920, "death_year": 2014},
            {"author_name": "Nam Cao", "biography": "Nhà văn hiện thực xuất sắc trước Cách mạng.", "birth_year": 1915, "death_year": 1951},
            {"author_name": "Vũ Trọng Phụng", "biography": "Nhà văn, nhà báo nổi bật với tác phẩm châm biếm xã hội.", "birth_year": 1912, "death_year": 1939},
            {"author_name": "Nguyễn Huy Thiệp", "biography": "Tác giả có phong cách sắc sảo và giàu tính phản biện.", "birth_year": 1950, "death_year": 2021},
            {"author_name": "Đỗ Bích Thúy", "biography": "Nhà văn viết nhiều về miền núi phía Bắc và thân phận con người.", "birth_year": 1975},
            {"author_name": "Nguyễn Phong Việt", "biography": "Tác giả thơ và tản văn được giới trẻ yêu thích.", "birth_year": 1980},
            {"author_name": "Hà Nhân", "biography": "Tác giả sách kỹ năng và tâm lý ứng dụng.", "birth_year": 1984},
            {"author_name": "Lê Minh Khuê", "biography": "Nhà văn nữ với nhiều truyện ngắn giàu chất hiện thực.", "birth_year": 1949},
            {"author_name": "Nguyễn Quang Thiều", "biography": "Nhà thơ, nhà văn với nhiều đóng góp cho văn học đương đại.", "birth_year": 1957},
            {"author_name": "Trần Đăng Khoa", "biography": "Nhà thơ, nhà báo với nhiều tác phẩm dành cho thiếu nhi.", "birth_year": 1958},
            {"author_name": "Lê Đạt", "biography": "Nhà thơ thuộc thế hệ đổi mới ngôn ngữ thi ca Việt Nam.", "birth_year": 1929, "death_year": 2008},
            {"author_name": "Xuân Quỳnh", "biography": "Nữ thi sĩ nổi tiếng với các bài thơ tình sâu sắc.", "birth_year": 1942, "death_year": 1988},
            {"author_name": "Nguyễn Duy", "biography": "Nhà thơ Việt Nam với giọng thơ gần gũi, giàu suy tư.", "birth_year": 1948},
            {"author_name": "Nguyễn Thị Thu Huệ", "biography": "Nhà văn với nhiều truyện ngắn về đời sống đô thị hiện đại.", "birth_year": 1966},
            {"author_name": "Đỗ Nhật Nam", "biography": "Tác giả trẻ với các sách truyền cảm hứng học tập và phát triển bản thân.", "birth_year": 2001},
        ]
        Author.objects.bulk_create([Author(**a) for a in authors])

        category_goc = Category.objects.create(
            category_name="Sách tiếng Việt",
            description="Các đầu sách xuất bản và phát hành bằng tiếng Việt.",
        )
        category_van_hoc = Category.objects.create(
            category_name="Văn học",
            parent_category=category_goc,
            description="Văn học Việt Nam và văn học thế giới bản dịch tiếng Việt.",
        )
        category_kinh_te = Category.objects.create(
            category_name="Kinh tế - Quản trị",
            parent_category=category_goc,
            description="Sách về kinh tế, quản trị và khởi nghiệp.",
        )
        category_ky_nang = Category.objects.create(
            category_name="Kỹ năng sống",
            parent_category=category_goc,
            description="Sách phát triển bản thân và kỹ năng mềm.",
        )
        category_thieu_nhi = Category.objects.create(
            category_name="Thiếu nhi",
            parent_category=category_goc,
            description="Sách dành cho thiếu nhi và tuổi mới lớn.",
        )

        Category.objects.bulk_create([
            Category(category_name="Tiểu thuyết Việt Nam", parent_category=category_van_hoc, description="Tiểu thuyết của các tác giả Việt Nam."),
            Category(category_name="Truyện ngắn Việt Nam", parent_category=category_van_hoc, description="Tuyển tập truyện ngắn hiện đại và cổ điển."),
            Category(category_name="Thơ Việt Nam", parent_category=category_van_hoc, description="Các tập thơ và tuyển thơ tiếng Việt."),
            Category(category_name="Văn học nước ngoài", parent_category=category_van_hoc, description="Tác phẩm văn học thế giới bản dịch tiếng Việt."),
            Category(category_name="Quản trị doanh nghiệp", parent_category=category_kinh_te, description="Sách điều hành doanh nghiệp và quản trị đội ngũ."),
            Category(category_name="Marketing - Bán hàng", parent_category=category_kinh_te, description="Sách về marketing, thương hiệu và bán hàng."),
            Category(category_name="Tài chính cá nhân", parent_category=category_kinh_te, description="Sách quản lý tài chính và đầu tư cho cá nhân."),
            Category(category_name="Tâm lý ứng dụng", parent_category=category_ky_nang, description="Sách tâm lý học ứng dụng trong đời sống."),
            Category(category_name="Giao tiếp - Thuyết trình", parent_category=category_ky_nang, description="Sách nâng cao giao tiếp và trình bày hiệu quả."),
            Category(category_name="Học tập hiệu quả", parent_category=category_ky_nang, description="Sách phương pháp học và tự học."),
            Category(category_name="Truyện tranh thiếu nhi", parent_category=category_thieu_nhi, description="Sách tranh và truyện tranh cho trẻ em."),
            Category(category_name="Văn học tuổi mới lớn", parent_category=category_thieu_nhi, description="Sách cho bạn đọc tuổi thiếu niên."),
            Category(category_name="Khoa học vui", parent_category=category_thieu_nhi, description="Sách khoa học phổ thông dễ hiểu cho trẻ em."),
        ])

        genres = [
            {"genre_name": "Tiểu thuyết", "description": "Tác phẩm hư cấu có dung lượng dài."},
            {"genre_name": "Truyện ngắn", "description": "Các truyện ngắn giàu tính cô đọng."},
            {"genre_name": "Tản văn", "description": "Các bài viết ngắn giàu cảm xúc và quan sát đời sống."},
            {"genre_name": "Thơ", "description": "Các tác phẩm thi ca tiếng Việt."},
            {"genre_name": "Tự truyện", "description": "Câu chuyện đời thực của tác giả."},
            {"genre_name": "Hồi ký", "description": "Ghi chép và hồi ức của nhân vật."},
            {"genre_name": "Kỹ năng mềm", "description": "Nội dung về giao tiếp, làm việc nhóm, quản lý thời gian."},
            {"genre_name": "Tâm lý học", "description": "Kiến thức tâm lý học ứng dụng."},
            {"genre_name": "Kinh doanh", "description": "Sách về chiến lược và vận hành kinh doanh."},
            {"genre_name": "Marketing", "description": "Sách về thương hiệu, tiếp thị và phát triển khách hàng."},
            {"genre_name": "Khởi nghiệp", "description": "Kinh nghiệm khởi nghiệp và phát triển sản phẩm."},
            {"genre_name": "Tài chính", "description": "Sách về quản trị tài chính cá nhân và doanh nghiệp."},
            {"genre_name": "Giáo dục", "description": "Sách về dạy học, học tập và phát triển năng lực."},
            {"genre_name": "Thiếu nhi", "description": "Sách dành cho bạn đọc nhỏ tuổi."},
            {"genre_name": "Khoa học thường thức", "description": "Kiến thức khoa học phổ thông dễ tiếp cận."},
            {"genre_name": "Lịch sử", "description": "Sách về lịch sử Việt Nam và thế giới."},
            {"genre_name": "Văn hóa - Xã hội", "description": "Phân tích đời sống văn hóa và xã hội đương đại."},
            {"genre_name": "Truyền cảm hứng", "description": "Sách tạo động lực tích cực trong học tập và công việc."},
        ]
        nhan_the_loai = [
            "Đương đại", "Cổ điển", "Ứng dụng", "Thực hành", "Chuyên sâu",
            "Phổ thông", "Nâng cao", "Nhập môn", "Dành cho người mới", "Nền tảng",
        ]
        linh_vuc = [
            "đời sống", "học đường", "công sở", "gia đình", "kinh doanh",
            "sáng tạo", "giao tiếp", "lãnh đạo", "quản lý", "xã hội",
        ]
        for i in range(1, 61):
            genres.append({
                "genre_name": f"Chuyên đề {nhan_the_loai[i % len(nhan_the_loai)]} {i}",
                "description": f"Thể loại tập trung vào {linh_vuc[i % len(linh_vuc)]}, trình bày theo hướng dễ áp dụng.",
            })
        Genre.objects.bulk_create([Genre(**g) for g in genres])

        publishers = [
            {"publisher_name": "Nhà xuất bản Trẻ", "contact_name": "Phòng kinh doanh", "phone": "02839316266", "address": "Thành phố Hồ Chí Minh", "website": "https://nxbtre.com.vn"},
            {"publisher_name": "Nhà xuất bản Kim Đồng", "contact_name": "Bộ phận phát hành", "phone": "02438221304", "address": "Hà Nội", "website": "https://nxbkimdong.com.vn"},
            {"publisher_name": "Nhà xuất bản Hội Nhà văn", "contact_name": "Bộ phận biên tập", "phone": "02439428629", "address": "Hà Nội", "website": "https://hoinhavanvietnam.vn"},
            {"publisher_name": "Nhà xuất bản Tổng hợp Thành phố Hồ Chí Minh", "contact_name": "Phòng phát hành", "phone": "02838253426", "address": "Thành phố Hồ Chí Minh", "website": ""},
            {"publisher_name": "Nhà xuất bản Lao Động", "contact_name": "Bộ phận liên hệ", "phone": "02438515380", "address": "Hà Nội", "website": ""},
            {"publisher_name": "Nhà xuất bản Thanh Niên", "contact_name": "Phòng đối tác", "phone": "02439434011", "address": "Hà Nội", "website": ""},
            {"publisher_name": "Nhà xuất bản Phụ Nữ Việt Nam", "contact_name": "Bộ phận phát hành", "phone": "02439710771", "address": "Hà Nội", "website": ""},
            {"publisher_name": "Nhà xuất bản Văn Học", "contact_name": "Phòng biên tập", "phone": "02439435372", "address": "Hà Nội", "website": ""},
            {"publisher_name": "Nhà xuất bản Đại học Quốc gia Hà Nội", "contact_name": "Phòng học thuật", "phone": "02437547061", "address": "Hà Nội", "website": ""},
            {"publisher_name": "Nhà xuất bản Đà Nẵng", "contact_name": "Phòng tổng hợp", "phone": "02363823238", "address": "Đà Nẵng", "website": ""},
            {"publisher_name": "Nhà xuất bản Hải Phòng", "contact_name": "Phòng phát hành", "phone": "02253840384", "address": "Hải Phòng", "website": ""},
            {"publisher_name": "Nhà xuất bản Cần Thơ", "contact_name": "Bộ phận liên hệ", "phone": "02923837883", "address": "Cần Thơ", "website": ""},
        ]
        tinh_thanh = [
            "Hà Nội", "Thành phố Hồ Chí Minh", "Đà Nẵng", "Cần Thơ", "Hải Phòng",
            "Huế", "Nha Trang", "Biên Hòa", "Vũng Tàu", "Buôn Ma Thuột",
            "Nam Định", "Quy Nhơn", "Phan Thiết", "Long Xuyên", "Vinh",
        ]
        for i in range(1, 61):
            publishers.append({
                "publisher_name": f"Công ty phát hành Sách Việt {i}",
                "contact_name": f"Bộ phận phát hành {i}",
                "phone": f"090{100000 + i}",
                "address": tinh_thanh[i % len(tinh_thanh)],
                "website": f"https://sachviet{i}.vn",
            })
        Publisher.objects.bulk_create([Publisher(**p) for p in publishers])

        self.stdout.write(self.style.SUCCESS(
            f"Created: {Author.objects.count()} authors, {Category.objects.count()} categories, "
            f"{Genre.objects.count()} genres, {Publisher.objects.count()} publishers"
        ))
