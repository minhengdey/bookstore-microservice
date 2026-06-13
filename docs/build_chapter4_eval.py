# -*- coding: utf-8 -*-
"""Chapter 4 sections 4.15–4.16."""

SEC_415 = r"""## 4.15 ĐÁNH GIÁ KẾT QUẢ TRIỂN KHAI

### 4.15.1 Các chức năng commerce đã hoàn thành

| Nhóm | Chức năng | Trạng thái | Bằng chứng code |
|------|-----------|------------|-----------------|
| Identity | Đăng ký, đăng nhập, phân role | Hoàn thành | `auth-service`, `login_view`, `register_view` |
| Catalog | Xem SP, lọc, flash sale | Hoàn thành | `product-service`, `product_list` |
| Cart | Thêm/sửa/xóa giỏ | Hoàn thành | `cart-service`, `view_cart` |
| Order | Đặt hàng legacy, theo dõi | Hoàn thành | `checkout`, `order_list` |
| Payment | COD + mock gateway | Hoàn thành | `order_pay`, `payment_callback` |
| Shipping | Tính phí, tạo vận đơn async | Hoàn thành | `shipping-service`, consumers |
| Promotion | Voucher, flash sale | Hoàn thành | `promotion-service`, checkout voucher API |
| Review/Wishlist | interaction-service | Hoàn thành | `product_review`, wishlist toggle |
| Support | Tickets customer/staff/admin | Hoàn thành | `support_*`, `staff_tickets` |
| Admin/Staff portal | Quản lý SP, đơn, KH | Hoàn thành | `admin_views`, `staff_views` |

**Chưa hoàn thành / ngoài scope:** OAuth, quên MK, payment gateway thật, checkout SAGA trên BFF, Kubernetes production.

### 4.15.2 Các chức năng AI đã hoàn thành

| Chức năng AI | Mô tả | Đánh giá |
|--------------|-------|----------|
| Hybrid Recommendation | CF + graph + category | Hoạt động trên home, `/recommendations/` |
| Behavior tracking | 8 action types | Đồng bộ recommender + interaction |
| RAG Chatbot | Groq + hybrid retrieval | Qua `/ai/chat/` proxy |
| Knowledge Base | pickle index | Cần `build_catalog_index` |
| Neo4j sync | recommender-consumer | Cần RabbitMQ + neo4j healthy |
| Next-action BiLSTM | prediction API | Có endpoint, UI hiển thị gián tiếp |
| MLOps admin API | retrain, rollback | Có trong recommender, admin portal một phần |

### 4.15.3 Hiệu năng

| Metric | Quan sát local Docker | Ghi chú |
|--------|----------------------|---------|
| Trang chủ TTFB | ~0.5–2s | Parallel fetch 2–3 API |
| Checkout POST | ~1–3s | Phụ thuộc reserve-stock |
| AI chat lần đầu | 10–30s | Model cold load |
| AI chat warm | 2–8s | Groq latency |
| Recommendation API | <1s thường | In-memory CF |

Cải thiện: warm-up recommender container, Redis cache recommendation ids, CDN static.

### 4.15.4 Trải nghiệm người dùng

- **Điểm mạnh:** Một domain duy nhất qua NGINX, không CORS, tiếng Việt status/price format, chatbot cùng origin.
- **Điểm yếu:** Không SPA — chuyển trang full reload; mobile responsive phụ thuộc CSS hiện có.

### 4.15.5 Độ chính xác Recommendation

Không có offline metric tự động trên production UI. Admin có `GET /api/v1/models/evaluation/` — cần chạy thủ công. Định tính sau seed behavior:
- User mua điện thoại → gợi ý phụ kiện cùng category
- User mới → trending/newest fallback ổn định

### 4.15.6 Chất lượng Chatbot

- Trả lời tiếng Việt mạch lạc khi `GROQ_API_KEY` hợp lệ và KB đã build
- Hallucination giảm nhờ context-only prompt
- Lỗi khi thiếu key hoặc recommender chưa ready — có message UX

### 4.15.7 Chất lượng GraphRAG

Graph context bổ sung retrieval khi user có history. Với user mới, graph sparse — RAG dựa chủ yếu text catalog. Neo4j cần event stream ổn định mới phát huy.

### Nhận xét mục 4.15

Hệ thống đạt mức **demo production-like**: commerce core đầy đủ, AI tích hợp có giá trị thực. Metric định lượng recommendation/chat cần bổ sung A/B test nếu triển khai thật."""

SEC_416 = r"""## 4.16 NHẬN XÉT CHƯƠNG

### 4.16.1 Hệ thống đã xây dựng được gì

Chương 4 đã chứng minh khả năng **hiện thực hóa** kiến trúc Chương 2 và AI Chương 3 thành hệ thống chạy được:

- Hơn **40 container** Docker Compose
- **14+ microservice** Django với database riêng
- **BFF storefront** Django Templates — không phải prototype tách rời
- **Luồng mua hàng end-to-end** từ đăng ký đến thanh toán COD/mock
- **AI layer** gợi ý + chat + behavior + graph

### 4.16.2 AI đóng vai trò gì

AI không thay thế commerce core mà **tăng giá trị trải nghiệm**:

1. **Cá nhân hóa** thứ tự sản phẩm trang chủ
2. **Thu thập tín hiệu** behavior xuyên suốt hành trình mua
3. **Tư vấn** qua chatbot RAG đa nguồn (text + graph)
4. **Mở rộng** candidate bằng Neo4j khi dữ liệu đủ

Thiết kế **fail-open**: recommender lỗi → fallback catalog mới nhất; checkout vẫn thành công.

### 4.16.3 Mức độ hoàn thiện

| Lớp | Mức hoàn thiện | Nhận xét |
|-----|----------------|----------|
| Commerce legacy | ~90% | Đủ demo và báo cáo |
| Commerce SAGA v2 | ~60% | Code có, UI chưa nối |
| AI recommendation | ~85% | Hybrid đầy đủ, metric UI thiếu |
| AI chatbot | ~80% | Phụ thuộc Groq external |
| DevOps | ~75% | Compose tốt, K8s chưa có |

### 4.16.4 Khả năng triển khai thực tế

Có thể deploy staging trên một máy chủ Docker đủ RAM (khuyến nghị 16GB+). Cần:
- Cấu hình `.env` secrets
- Seed data `scripts/seed_all.sh`
- Build KB `build_catalog_index`
- Health check NGINX → gateway → services

Chưa sẵn sàng traffic lớn production mà không thêm: load balancer, DB replication, secret rotation, monitoring.

### 4.16.5 Khả năng mở rộng

| Hướng mở rộng | Cách thức có sẵn trong kiến trúc |
|---------------|-----------------------------------|
| Scale AI | Tách `recommender-ai-service` replica, shared Neo4j |
| Scale catalog | Chuyển storefront sang `catalog-service` + SAGA |
| Frontend SPA | Thay templates bằng React gọi cùng BFF JSON APIs |
| Payment thật | Nối `payment-service` webhook VNPay thật |
| Vector DB | Thay pickle bằng pgvector / Qdrant khi catalog lớn |

### 4.16.6 Kết luận chương

Chương 4 cho thấy quá trình xây dựng không chỉ là "ghép module" mà là **tích hợp có chủ đích**: BFF orchestration, async outbox, AI sidecar, behavior flywheel (xem → giỏ → mua → gợi ý tốt hơn). Người đọc có thể lần theo `api-gateway/gateway/views.py` và `recommender-ai-service/app/` để tái hiện từng luồng đã mô tả.

**Sẵn sàng Chương 5** (nếu có): kiểm thử, đo lường, hoặc triển khai production hardening."""
