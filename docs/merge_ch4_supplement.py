# -*- coding: utf-8 -*-
"""Supplement chapter 4 with additional technical depth."""
from pathlib import Path
import re

TARGET = Path(__file__).parent / "CHUONG4_TAI_LIEU_TICH_HOP_VA_TRIEN_KHAI.md"
MARKER = "## 4.16 NHẬN XÉT CHƯƠNG"

SUPPLEMENT = r"""
## PHỤ LỤC TRIỂN KHAI — CHI TIẾT BỔ SUNG

### P.1 Bảng ánh xạ URL Gateway → Microservice

Bảng dưới giúp trace nhanh khi đọc `gateway/urls.py`:

| URL Gateway (HTML) | View function | Service được gọi |
|--------------------|---------------|------------------|
| `/` | `home` | product, recommender (customer) |
| `/login/` | `login_view` | auth |
| `/register/` | `register_view` | auth |
| `/products/` | `product_list` | product, categories |
| `/products/{id}/` | `product_detail` | product, interaction, cart |
| `/cart/{cid}/` | `view_cart` | cart, product |
| `/cart/{cid}/checkout/` | `checkout` | cart, user, ship, order, product |
| `/orders/{id}/pay/` | `order_pay` | order, payment |
| `/orders/` | `order_list` | order |
| `/ai/chat/` | `ai_chat_proxy` | recommender |
| `/recommendations/` | `recommendation_list` | recommender, product |
| `/profile/` | `profile_view` | user |
| `/admin/dashboard/` | `admin_dashboard` | order, product, user |

### P.2 File source code quan trọng nhất

| File | Số dòng (xấp xỉ) | Nội dung |
|------|------------------|----------|
| `api-gateway/gateway/views.py` | 2200+ | Toàn bộ orchestration storefront |
| `api-gateway/gateway/behavior_tracking.py` | 220 | AI event tracking |
| `docker-compose.yml` | 1130 | Toàn bộ infrastructure |
| `recommender-ai-service/app/services/recommender_service.py` | 460+ | Hybrid recommendation |
| `recommender-ai-service/rag/hybrid_retriever.py` | 350+ | RAG retrieval |
| `recommender-ai-service/rag/rag_llm.py` | 200+ | LLM integration |

### P.3 Biến môi trường AI quan trọng

| Biến | Service | Tác dụng |
|------|---------|----------|
| `GROQ_API_KEY` | recommender | Chat LLM |
| `EMBEDDING_MODEL` | recommender | SentenceTransformer model |
| `GRAPH_KB_PATH` | recommender | Đường dẫn graph_kb.json |
| `NEO4J_URI` | recommender | Bolt connection |
| `PRODUCT_SERVICE_URL` | recommender | Sync catalog |
| `ORDER_SERVICE_URL` | recommender | Co-purchase orders |

### P.4 Lệnh vận hành thường dùng khi demo

```bash
docker-compose up -d
docker-compose exec recommender-ai-service python manage.py build_catalog_index
docker-compose exec recommender-ai-service python manage.py seed_mock
bash scripts/seed_all.sh
```

### P.5 Troubleshooting triển khai

| Triệu chứng | Nguyên nhân có thể | Cách xử lý |
|-------------|-------------------|------------|
| Trang chủ không có gợi ý | Recommender chưa seed behavior | Chạy seed_mock, đăng nhập customer |
| Chatbot 503 | GROQ_API_KEY thiếu hoặc recommender down | Kiểm tra env, logs container |
| Checkout lỗi reserve stock | product-service hoặc hết hàng | Kiểm tra stock trong product_db |
| Auth unavailable | auth-db chưa healthy | `docker-compose ps`, đợi healthcheck |

### P.6 So sánh legacy order vs SAGA v2

| Tiêu chí | Legacy (`POST /orders/`) | SAGA v2 (`POST /api/v1/orders/checkout/`) |
|----------|--------------------------|-------------------------------------------|
| Storefront BFF | **Đang dùng** | Chưa nối |
| Reserve stock | product-service internal | inventory-service |
| Catalog | product-service | catalog-service |
| Compensation | Thủ công / hạn chế | OrderSagaManager |
| Code location | `order/legacy_*` | `order/services/saga_manager.py` |

### P.7 Checklist bảo vệ đồ án — demo live

1. `docker-compose ps` — tất cả healthy
2. Đăng ký customer mới → home thấy sản phẩm
3. Xem SP → thêm giỏ → checkout COD → đơn thành công
4. Quay lại home — thứ tự SP có thể thay đổi (AI)
5. Mở chatbot — hỏi "gợi ý điện thoại" — nhận answer + products
6. Admin portal — xem đơn, sản phẩm

---

"""


def main():
    text = TARGET.read_text(encoding="utf-8")
    if MARKER not in text:
        raise SystemExit(f"Marker not found: {MARKER}")
    if "## PHỤ LỤC TRIỂN KHAI" in text:
        print("Supplement already merged")
        return
    parts = text.split(MARKER, 1)
    new_text = parts[0] + SUPPLEMENT + "\n" + MARKER + parts[1]
    TARGET.write_text(new_text, encoding="utf-8")
    words = len(re.findall(r"\w+", new_text))
    print(f"Merged supplement. Words: {words}, Lines: {len(new_text.splitlines())}")


if __name__ == "__main__":
    main()
