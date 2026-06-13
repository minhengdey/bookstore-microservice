# -*- coding: utf-8 -*-
"""Chapter 4 sections 4.2–4.11 (core technical content)."""

SEC_42 = r"""## 4.2 KIẾN TRÚC TRIỂN KHAI THỰC TẾ

### 4.2.1 Sơ đồ kiến trúc hệ thống

Sơ đồ dưới đây mô tả **luồng thực tế** khi người dùng truy cập website — không phải sơ đồ lý thuyết từ Chương 2.

```mermaid
flowchart TB
    subgraph Client["Client (Trình duyệt)"]
        BR[HTTP Request]
    end
    subgraph Edge["Edge Layer"]
        NG[NGINX :80<br/>rate limit + auth_request]
    end
    subgraph Frontend["Frontend (Django Templates)"]
        GW[api-gateway :8000<br/>BFF + HTML + static JS]
    end
    subgraph Backend["Backend API (Microservices)"]
        AUTH[auth-service]
        USER[user-service]
        PROD[product-service]
        CART[cart-service]
        ORD[order-service]
        PAY[payment-service]
        SHIP[shipping-service]
        PROM[promotion-service]
        INT[interaction-service]
    end
    subgraph Database["Database Layer"]
        PG[(PostgreSQL x14<br/>mỗi service 1 DB)]
        RD[(Redis)]
        MQ[RabbitMQ]
    end
    subgraph AI["AI Service Layer"]
        REC[recommender-ai-service :8011]
        KB[(catalog_hybrid_index.pkl<br/>Knowledge Base)]
        VEC[Vector index in-memory<br/>TF-IDF + embeddings]
        GJSON[(graph_kb.json)]
        N4J[(Neo4j :7687)]
        RE[Recommendation Engine<br/>RecommenderService]
        LLM[Groq API LLM<br/>rag_llm.py]
    end

    BR -->|GET /products/| NG
    NG -->|proxy| GW
    GW -->|REST nội bộ| PROD
    GW -->|REST nội bộ| CART
    GW -->|REST nội bộ| ORD
    GW -->|POST /ai/chat/| REC
    PROD --> PG
    ORD --> PG
    ORD --> MQ
    REC --> KB
    REC --> VEC
    REC --> GJSON
    REC --> N4J
    REC --> RE
    REC --> LLM
    REC -->|hydrate product| PROD
    GW --> AUTH
    AUTH --> PG
```

**Phân tích sơ đồ:** Người dùng **không** gọi trực tiếp microservice. Mọi request đi qua NGINX → `api-gateway`. Gateway vừa render HTML (frontend), vừa gọi REST nội bộ bằng `requests` (`views.py`, biến `SVC = settings.SERVICE_URLS`). AI Service là container độc lập; gateway chỉ **proxy** chat qua `/ai/chat/` để tránh CORS.

### 4.2.2 Vai trò từng thành phần

| Thành phần | Vai trò | File / container tham chiếu |
|------------|---------|----------------------------|
| **Client** | Gửi HTTP, lưu session cookie Django | Trình duyệt |
| **NGINX** | Reverse proxy, rate limit, `auth_request` introspect JWT | `nginx/nginx.conf`, container `nginx` |
| **Frontend** | Template HTML + vanilla JS infinite scroll | `api-gateway/templates/`, `static/` |
| **Backend API** | Nghiệp vụ tách domain | 14 service trong `docker-compose.yml` |
| **Database** | Persistence theo service | `*-db` containers |
| **AI Service** | Gợi ý + chat RAG | `recommender-ai-service/` |
| **Knowledge Base** | Catalog text đã chunk/index | `rag/catalog_hybrid_index.pkl` |
| **Vector Database** | Embedding + TF-IDF in-memory | `HybridProductRetriever` — **không ChromaDB/FAISS persistent** |
| **Neo4j** | Đồ thị user–product cho pipeline GNN | container `neo4j`, `recommendation_pipeline.py` |
| **Recommendation Engine** | Hybrid CF + co-occurrence + category | `RecommenderService` |
| **LLM** | Sinh câu trả lời chatbot | Groq qua `rag/rag_llm.py` |

### 4.2.3 Luồng request — ví dụ khách xem trang chủ

1. **Client** gửi `GET /` kèm session cookie.
2. **NGINX** chuyển tiếp tới `api-gateway:8000`.
3. **Gateway** `home()` đọc JWT từ session, xác định role (`permissions.py`).
4. Nếu **customer**: gọi song song:
   - `GET product-service/products/?flash_sale=true`
   - `GET product-service/categories/`
   - `GET recommender-ai-service/recommendations/{entity_id}/`
5. **product-service** truy vấn `product_db`, trả JSON.
6. **recommender-ai-service** đọc behavior từ `recommender_db`, chạy `RecommenderService.recommend()`, trả `recommended_product_ids`.
7. Gateway hydrate product detail từ product-service, format giá VND (`_fmt_product`), render `home.html`.

### 4.2.4 Luồng response

Response luôn là **HTML** (storefront) hoặc **JSON** (API phụ: `/api/home/products/`, `/ai/chat/`). Gateway không trả raw microservice response cho user — nó **biến đổi** dữ liệu:
- Format tiền: `_fmt_vnd()`
- Format ngày: `_fmt_date()`
- Dịch trạng thái: `ORDER_STATUS_VI`, `PRODUCT_STATUS_VI`
- Gộp nhiều API thành một context template

### 4.2.5 Luồng request — đặt hàng (legacy)

```mermaid
sequenceDiagram
    participant U as User
    participant GW as api-gateway
    participant C as cart-service
    participant US as user-service
    participant SH as shipping-service
    participant O as order-service
    participant P as product-service
    participant PAY as payment-service
    participant MQ as RabbitMQ

    U->>GW: POST /cart/{id}/checkout/
    GW->>C: GET /carts/{id}/
    GW->>US: GET addresses
    GW->>SH: POST /api/shipping/calculate-fee/
    GW->>O: POST /orders/
    O->>P: POST /internal/reserve-stock/
    O-->>GW: order_id
    GW->>C: DELETE /carts/{id}/
    GW-->>U: redirect /orders/{id}/pay/
    U->>GW: POST pay (COD)
    GW->>PAY: POST /payments/
    PAY->>MQ: payment.confirmed
    GW->>REC: track purchase events
```

**Phân tích:** Storefront dùng luồng **legacy** `POST order-service/orders/`, không gọi SAGA `POST /api/v1/orders/checkout/` của `catalog-service` + `inventory-service`. Đây là điểm quan trọng khi đối chiếu Chương 2 với triển khai thực tế.

### Nhận xét mục 4.2

Kiến trúc triển khai là **BFF + microservices + AI sidecar**. AI không nằm trong critical path đặt hàng nhưng ảnh hưởng trải nghiệm (gợi ý, chat, behavior tracking)."""

SEC_43 = r"""## 4.3 CẤU TRÚC SOURCE CODE

### 4.3.1 Tổng quan monorepo

Repository `e-commerce` tổ chức theo **monorepo microservice**: mỗi thư mục top-level là một service độc lập có `Dockerfile`, `requirements.txt`, `manage.py` (Django) hoặc FastAPI.

```
e-commerce/
├── api-gateway/          # BFF + storefront templates
├── auth-service/
├── user-service/
├── product-service/      # Catalog storefront (legacy)
├── catalog-service/      # Catalog v2 (SAGA)
├── inventory-service/    # Tồn kho v2
├── cart-service/
├── order-service/
├── payment-service/
├── shipping-service/
├── promotion-service/
├── interaction-service/  # Review, wishlist, tickets
├── notification-service/
├── recommender-ai-service/  # AI: RAG + recommender + Neo4j
├── common/               # Shared auth client, middleware
├── nginx/
├── scripts/              # E2E test, seed
├── docker-compose.yml
└── docs/                 # Tài liệu đồ án
```

### 4.3.2 Vai trò từng thư mục chính

#### api-gateway/

| Thư mục / file | Vai trò |
|----------------|---------|
| `gateway/views.py` | Logic BFF: login, home, checkout, AI proxy (~2200 dòng) |
| `gateway/urls.py` | Route storefront (~98 paths) |
| `gateway/behavior_tracking.py` | Gửi event tới recommender + interaction |
| `gateway/admin_views.py` | Portal quản trị |
| `gateway/staff_views.py` | Portal nhân viên |
| `templates/` | HTML Django (home, checkout, product_detail...) |
| `static/` | CSS, JS (infinite scroll, chatbot widget embed) |

**Vì sao BFF tách riêng:** Tránh CORS, gom nhiều API, giữ session server-side, render SEO-friendly HTML. Khách hàng không cần SPA phức tạp.

#### recommender-ai-service/

| Thư mục | Vai trò |
|---------|---------|
| `app/views/` | API: recommendations, chat, events |
| `app/services/` | `recommender_service.py`, `graph/`, pipeline |
| `app/repositories/` | Truy vấn `recommender_db` |
| `rag/` | `hybrid_retriever.py`, `rag_llm.py`, `intent_router.py` |
| `app/management/commands/` | `build_catalog_index`, `train_implicit_cf_local` |
| `static/` | `chatbot-widget.js` |

#### common/

Thư viện dùng chung: `InternalClient` ký HMAC request nội bộ, middleware xác thực service-to-service. Tránh copy-paste auth logic 14 lần.

### 4.3.3 Cấu trúc điển hình một microservice Django

Mỗi `*-service/` tuân pattern:

```
*-service/
├── Dockerfile
├── entrypoint.sh       # migrate + seed + runserver/gunicorn
├── manage.py
├── *_service/
│   ├── settings.py     # DB, RabbitMQ, Redis env
│   ├── urls.py
│   └── wsgi.py
└── <app_name>/
    ├── models.py
    ├── views.py / viewsets
    ├── serializers.py
    ├── urls.py
    ├── services.py     # business logic
    └── migrations/
```

**Ưu điểm:**
- Service độc lập deploy, scale, migrate DB riêng
- Lỗi một service không sập toàn bộ (circuit breaker ở gateway qua timeout/retry)
- Team có thể phân công theo domain

**Hạn chế:**
- Phức tạp vận hành (40+ container trong `docker-compose.yml`)
- Distributed transaction cần SAGA/outbox (đã có code v2, storefront chưa dùng hết)

### 4.3.4 Luồng import và phụ thuộc

- **Gateway → Services:** HTTP sync qua `SERVICE_URLS` trong `settings.py`
- **Services → Services:** Internal endpoints (`/internal/...`) + HMAC headers
- **Services → RabbitMQ:** Outbox pattern (`payment-outbox-worker`, `order-outbox-worker`)
- **recommender-consumer:** Nghe event, cập nhật Neo4j + behavior
- **AI → product-service:** Hydrate metadata sản phẩm khi recommend/chat

### Nhận xét mục 4.3

Cấu trúc source phản ánh **domain-driven decomposition**. Storefront tập trung ở `api-gateway`; AI tập trung ở `recommender-ai-service` — ranh giới rõ, dễ mở rộng."""

SEC_44 = r"""## 4.4 CÔNG NGHỆ SỬ DỤNG

> Chỉ liệt kê công nghệ **có trong source code**. Công nghệ không tìm thấy được ghi rõ.

### 4.4.1 Frontend — Django Templates + Vanilla JavaScript

| Công nghệ | Vai trò | Lý do chọn | Tích hợp | Ưu điểm | Hạn chế |
|-----------|---------|------------|----------|---------|---------|
| **Django Templates** | Render HTML server-side | Gateway đã là Django; không cần thêm build toolchain SPA | `render(request, "home.html", ctx)` trong `views.py` | SEO tốt, session đơn giản, ít dependency JS | UX động kém hơn React |
| **Vanilla JS** | Infinite scroll, AJAX voucher/shipping | Tránh webpack phức tạp cho đồ án | `static/js/`, fetch `/api/home/products/` | Nhẹ, không lock-in framework | Khó maintain UI lớn |

**ReactJS / NextJS / VueJS:** Không tìm thấy trong source code dự án. Frontend thực tế là Django Templates.

### 4.4.2 Backend — Django + Django REST Framework

| Công nghệ | Vai trò | Lý do | Tích hợp |
|-----------|---------|-------|----------|
| **Django 4.x** | Framework chính 14+ service | Mature ORM, admin, ecosystem | Mỗi service `manage.py` |
| **Django REST Framework** | REST API | Serializer, ViewSet, pagination | `order-service`, `interaction-service`, `catalog-service`... |
| **Gunicorn** | WSGI production | Entrypoint container | `entrypoint.sh` |

**FastAPI:** Không dùng cho core commerce. AI service cũng là Django (không phải FastAPI).

### 4.4.3 Database — PostgreSQL

| Công nghệ | Vai trò | Lý do | Tích hợp |
|-----------|---------|-------|----------|
| **PostgreSQL 15** | Primary DB mỗi service | ACID, JSON field, mature | 14 container `*-db` trong compose |
| **Redis 7** | Cache session gateway, order lock | Nhanh, ephemeral | `redis`, `order-redis` |

**MySQL / SQLite:** Không dùng production (chỉ có thể test local đơn lẻ).

### 4.4.4 Message Queue — RabbitMQ

| Vai trò | Lý do | Tích hợp |
|---------|-------|----------|
| Async: payment → shipping, order events → AI | Tách synchronous checkout khỏi side-effect | `payment-consumer`, `recommender-consumer`, outbox workers |

### 4.4.5 AI & ML

| Công nghệ | Vai trò | File tham chiếu | Ghi chú |
|-----------|---------|-----------------|---------|
| **Sentence Transformers** | Embedding catalog | `hybrid_retriever.py`, `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` |
| **scikit-learn** | TF-IDF, TruncatedSVD, cosine | `hybrid_retriever.py` | Sparse + dense hybrid |
| **Groq API** | LLM chatbot | `rag/rag_llm.py` | Cần `GROQ_API_KEY` |
| **implicit / ALS** | Collaborative filtering | `implicit_cf_engine.py` | Matrix factorization |
| **BiLSTM** | Next-action prediction | `behavior_prediction_service.py` | Artifact pickle |
| **NetworkX** | Graph KB fallback | `rag_llm.py` | Khi Neo4j/json graph |
| **Neo4j 5** | Graph store runtime | `recommendation_pipeline.py` | bolt://neo4j:7687 |
| **numpy** | Vector ops | Khắp recommender-ai-service | In-memory similarity |

**LangChain / LlamaIndex:** Không tìm thấy import trong `requirements.txt` recommender-ai-service.

**ChromaDB / FAISS persistent:** Không dùng. Vector index lưu trong `catalog_hybrid_index.pkl`, load RAM qua `pickle`.

**OpenAI API:** Không dùng. LLM thực tế là Groq.

**HuggingFace:** Dùng gián tiếp qua `sentence-transformers` model trên HuggingFace Hub.

### 4.4.6 Deployment

| Công nghệ | Vai trò | File |
|-----------|---------|------|
| **Docker** | Đóng gói mỗi service | `*/Dockerfile` |
| **Docker Compose** | Orchestration local/staging | `docker-compose.yml` (~1130 dòng) |
| **NGINX** | Reverse proxy, TLS termination ready | `nginx/` |

**Kubernetes:** Không tìm thấy manifest trong repo.

### Nhận xét mục 4.4

Stack thực tế là **Django microservices + Django BFF + Python AI service**. Không có SPA framework. AI stack tự xây (RAG hybrid + Groq) thay vì LangChain — giảm dependency, tăng kiểm soát pipeline."""

SEC_45 = r"""## 4.5 XÂY DỰNG BACKEND

Phần này phân tích **các domain service** mà storefront thực sự gọi. Review nằm trong `interaction-service` (không có `review-service` riêng).

### 4.5.1 Authentication (auth-service)

#### Mục tiêu
Xác thực danh tính, cấp JWT, hỗ trợ NGINX `auth_request` introspect.

#### Chức năng
- Đăng ký tài khoản (`RegisterView`)
- Đăng nhập theo role customer/staff/admin (`LoginView`)
- Refresh token (`RefreshView`)
- Introspect token cho edge proxy (`IntrospectTokenView`)
- Rate limit login theo IP (`_rate_limit_login`)

#### API

| Method | Endpoint | Chức năng |
|--------|----------|-----------|
| POST | `/auth/register/` | Tạo user + customer profile |
| POST | `/auth/login/` | Trả `access`, `refresh`, `user` |
| POST | `/auth/refresh/` | Làm mới access token |
| GET | `/auth/introspect/` | Validate token (NGINX) |
| GET | `/users/me/` | Profile JWT hiện tại |

#### Code Structure

Gateway không xử lý auth trực tiếp — chỉ proxy:

```python
# api-gateway/gateway/views.py — login_view
r = requests.post(
    f"{SVC['auth']}/auth/login/",
    json={"username": username, "password": password, "role": login_type},
    timeout=5,
)
if r.status_code == 200:
    data = r.json()
    request.session["access_token"] = data["access"]
    request.session["user"] = data["user"]
```

`auth-service` dùng `AuthService.register()` / `login()` trong `authentication/services.py`, ghi audit `AuthAudit`, hash password Django.

#### Database Interaction
- Bảng user, role mapping trong `auth_db` (PostgreSQL container `auth-db`)
- Redis/cache cho rate limit login

---

### 4.5.2 User Service (user-service)

#### Mục tiêu
Quản lý profile, địa chỉ giao hàng — phục vụ checkout.

#### Chức năng
- CRUD địa chỉ (`AddressListView`, `AddressDetailView`)
- Profile nội bộ (`UserProfileView`)
- Danh sách customer cho staff (`CustomerListView`)

#### API chính (gateway gọi)

| Method | Endpoint | Khi nào gọi |
|--------|----------|-------------|
| GET | `/internal/users/{uuid}/addresses/` | Checkout GET — load địa chỉ |
| POST | `/internal/users/{uuid}/addresses/` | Thêm địa chỉ từ profile/checkout |
| PUT | `/internal/users/{uuid}/addresses/{id}/` | Đặt default, sửa địa chỉ |

#### Luồng checkout
`checkout()` gọi `_resolve_user_address()` → `GET user-service` addresses → validate snapshot → embed vào `shipping_address` khi `POST order-service/orders/`.

#### Database
- `user_db`: bảng `Address`, `UserProfile`, liên kết `customer_id`

---

### 4.5.3 Product Service (product-service)

#### Mục tiêu
Catalog **storefront** — sản phẩm, category, brand, variant, tồn kho đơn giản.

#### Chức năng
- CRUD sản phẩm (staff/admin qua gateway)
- Flash sale sync (`InternalSyncFlashSalesView`)
- Reserve/release stock nội bộ khi đặt hàng legacy

#### API

| Method | Endpoint | Gateway sử dụng |
|--------|----------|-----------------|
| GET | `/products/` | home, product_list, checkout hydrate |
| GET | `/products/{id}/` | product_detail |
| GET | `/categories/` | home, filter |
| POST | `/internal/reserve-stock/` | order-service gọi khi tạo đơn |

#### Code minh họa — format giá ở gateway

```python
# views.py — _fmt_product
effective = _product_effective_price(p)  # flash_sale_price nếu đang sale
return {
    **p,
    "display_price_fmt": _fmt_vnd(effective),
    "is_flash_sale_active": on_flash_sale,
}
```

#### Database
- `product_db`: `Product`, `Category`, `Brand`, `ProductVariant`, `InventoryTransaction`

**Lưu ý:** `catalog-service` là catalog v2 cho SAGA; **UI storefront dùng product-service**.

---

### 4.5.4 Order Service (order-service)

#### Mục tiêu
Tạo và quản lý đơn hàng. Có **hai** implementation song song.

#### Luồng legacy (storefront đang dùng)

| Bước | API | Xử lý |
|------|-----|-------|
| 1 | `POST /orders/` | Tạo order + items |
| 2 | (nội bộ) | Gọi `product-service/internal/reserve-stock/` |
| 3 | Trả `id` | Gateway redirect thanh toán |

#### Luồng SAGA v2 (có code, BFF chưa gọi)

```python
# order-service — OrderViewSet.checkout
order = OrderSagaManager.start_checkout(
    user_id=str(user_id),
    cart_items=cart_items,
    shipping_address=shipping_address
)
```

#### API legacy gateway dùng

| Method | Endpoint | Chức năng |
|--------|----------|-----------|
| GET, POST | `/orders/` | Danh sách / tạo đơn |
| GET, PUT | `/orders/{id}/` | Chi tiết / cập nhật trạng thái |
| POST | `/orders/{id}/return/` | Yêu cầu trả hàng |

#### Database
- `order_db`: `Order`, `OrderItem`, `OrderSaga` (v2), outbox tables

---

### 4.5.5 Payment Service (payment-service)

#### Mục tiêu
Ghi nhận thanh toán, publish event RabbitMQ → kích hoạt shipping.

#### Chức năng
- Liệt kê phương thức (`PaymentMethodListView`)
- Xử lý thanh toán (`PaymentListCreateView.post` → `PaymentService.process_payment`)
- Mock gateway VNPay/MoMo qua UI gateway

#### API

| Method | Endpoint | Input chính | Output |
|--------|----------|-------------|--------|
| GET | `/payment-methods/` | JWT | Danh sách COD, VNPay Mock... |
| POST | `/payments/` | `order_id`, `payment_amount`, `payment_method_id` | Payment record |

#### Code gateway — COD vs Mock

```python
# order_pay — COD gọi payment ngay
r = _post(f"{SVC['pay']}/payments/", json={
    "order_id": order_id,
    "payment_amount": amount_float,
    "payment_method_id": int(method_id),
}, request=request)
track_order_purchases(request, order)  # AI behavior
```

Mock gateway render `payment_gateway_mock.html` → callback `payment_callback` → mới POST payment.

#### Database + Async
- `payment_db`: Payment, PaymentMethod
- `payment-outbox-worker` → RabbitMQ → `shipping-consumer`

---

### 4.5.6 Review Service → interaction-service

**Không có review-service riêng.** Review nằm trong `interaction-service`:

| Method | Endpoint | Chức năng |
|--------|----------|-----------|
| GET, POST | `/api/v1/interactions/reviews/` | Đánh giá sản phẩm |
| POST | `/api/v1/interactions/interactions/` | Event bus (VIEW, PURCHASE...) |

Gateway `product_review()` gọi interaction-service khi đơn ở trạng thái `DELIVERED`/`COMPLETED`. `track_behavior(..., "review")` cập nhật recommender.

### Nhận xét mục 4.5

Backend triển khai đầy đủ commerce core. Điểm cần nhớ khi đọc code: **gateway là orchestrator** — đọc `views.py` để hiểu luồng thực tế, không chỉ đọc từng service độc lập."""

SEC_46 = r"""## 4.6 XÂY DỰNG AI SERVICE

`recommender-ai-service` là trung tâm AI — gợi ý, chat RAG, behavior, Neo4j sync.

### 4.6.1 AI Gateway (trong E-Commerce)

Strictly speaking không có service tên "AI Gateway" riêng. **Vai trò AI Gateway** do `api-gateway` đảm nhiệm:

| Endpoint BFF | Upstream | Mục đích |
|--------------|----------|----------|
| `POST /ai/chat/` | `recommender/api/recommender/chat-ktmp` | Proxy chat, tránh CORS |
| (nội bộ) | `GET recommender/recommendations/{id}/` | Gợi ý trang chủ |
| `behavior_tracking.py` | `POST recommender/api/recommender/events/` | Ghi hành vi |

```python
# ai_chat_proxy — retry 3 lần, timeout 90s
r = SESSION.post(f"{SVC['recommender']}/api/recommender/chat-ktmp", json=body, timeout=90)
```

### 4.6.2 Chat Engine (KTMP RAG)

**Input:** JSON `{message, user_id, history, recent_behaviors}`

**Pipeline:**
1. `KTMPChatConsultingView.post()` nhận request
2. `AIModelSingleton.get_ktmp_rag_llm()` lazy-load model
3. `rag_llm.chat()` → `intent_router` phân loại intent
4. `HybridProductRetriever` retrieval catalog
5. Groq API sinh `answer` + attach `products`

**Output:** `{answer, products, intent, context_used}`

### 4.6.3 RAG Engine

File: `rag/hybrid_retriever.py`

| Giai đoạn | Kỹ thuật | Output |
|-----------|----------|--------|
| Index build | `build_catalog_index` command | `catalog_hybrid_index.pkl` |
| Sparse | TF-IDF + cosine | Top-K sparse |
| Dense | SentenceTransformer embedding | Top-K dense |
| Fusion | RRF (Reciprocal Rank Fusion) | Candidate pool |
| Rerank | `product_reranker` | Final context docs |

### 4.6.4 GraphRAG Engine

Hai lớp graph trong hệ thống:

1. **graph_kb.json** (`GraphRepository`) — lightweight JSON graph cho RAG context
2. **Neo4j** (`recommendation_pipeline.py`) — graph walk cho candidate retrieval GNN pipeline

```python
# recommendation_pipeline.py (rút gọn)
candidates = RecommendationPipeline._retrieve_candidates_neo4j(user_id)
```

GraphRAG mở rộng ngữ cảnh: từ query user → retrieve product → leo cạnh `BELONGS_TO` (category), `INTERACTED` (behavior).

### 4.6.5 Recommendation Engine

`RecommenderService` — hybrid 5 chiến lược:

1. Implicit CF (ALS/NMF)
2. Item co-occurrence
3. Co-purchase từ order history
4. Category affinity
5. Cold-start fallback

**Input:** `customer_id`, optional `prediction` từ BiLSTM

**Output:** `recommended_product_ids`, `strategy`, `recommendation_scores`

### 4.6.6 Sequence Diagram — Chat request

```mermaid
sequenceDiagram
    participant U as Browser
    participant GW as api-gateway
    participant REC as recommender-ai-service
    participant RAG as HybridRetriever
    participant GROQ as Groq API
    participant PROD as product-service

    U->>GW: POST /ai/chat/ {message, user_id, history}
    GW->>REC: POST /api/recommender/chat-ktmp
    REC->>RAG: retrieve(message)
    RAG-->>REC: top-K products + context
    REC->>GROQ: prompt + context
    GROQ-->>REC: answer text
    REC->>PROD: hydrate (nếu cần)
    REC-->>GW: {answer, products, intent}
    GW-->>U: JSON response
```

### Nhận xét mục 4.6

AI Service tách biệt deploy, scale độc lập. Lazy-load model lần đầu có thể timeout — gateway đã retry và trả 504 có message hướng dẫn user."""

SEC_47 = r"""## 4.7 TÍCH HỢP AI VÀ HỆ THỐNG THƯƠNG MẠI ĐIỆN TỬ

Đây là phần mô tả **end-to-end** cách AI gắn vào storefront — từ hành vi người dùng đến kết quả hiển thị.

### 4.7.1 Tổng quan luồng tích hợp

```mermaid
flowchart TD
    A[Người dùng truy cập website] --> B{Tìm kiếm / duyệt SP}
    B --> C[Gateway track_behavior]
    C --> D[recommender events API]
    C --> E[interaction-service events]
    B --> F{Hỏi chatbot?}
    F -->|Có| G[POST /ai/chat/]
    G --> H[RAG HybridRetriever]
    H --> I[Knowledge Base pickle]
    H --> J[Graph context graph_kb.json]
    G --> K[Groq LLM]
    B --> L[Trang chủ customer]
    L --> M[GET recommendations/customer_id]
    M --> N[RecommenderService hybrid]
    N --> O[Neo4j + behavior DB]
    N --> P[Ranking Top-N]
    P --> Q[Hiển thị home.html]
```

### 4.7.2 Bước 1 — Người dùng truy cập website

- Request `GET /` qua NGINX → `home()` trong gateway.
- Session Django lưu JWT sau login; `_role()` và `_entity_id()` đọc từ `request.session["user"]`.
- Không gọi AI nếu user là guest thuần — chỉ load `product-service/products/?sort_by=newest`.

### 4.7.3 Bước 2 — Tìm kiếm / xem sản phẩm

`product_list` và `product_detail` gọi `track_behavior(request, customer_id, product_id, "view")` khi customer đã đăng nhập.

```python
# behavior_tracking.py
requests.post(f"{SVC['recommender']}/api/recommender/events/", json={
    "customer_id": customer_id,
    "product_id": product_id,
    "action": action,  # view, add_to_cart, purchase...
    "session_id": session_id,
    "device": device,
    "persona": persona,
})
```

Song song gửi `interaction-service` với `event_type: VIEW` — phục vụ analytics và đồng bộ sau này.

### 4.7.4 Bước 3 — AI phân tích truy vấn (chat)

Khi user gõ câu hỏi chatbot, `intent_router` phân loại: tư vấn sản phẩm, tra cứu đơn, chào hỏi... Intent quyết định có gọi retrieval hay không.

### 4.7.5 Bước 4 — Knowledge Base truy xuất

`HybridProductRetriever.retrieve(query)`:
- Load `catalog_hybrid_index.pkl` (TF-IDF matrix + embeddings)
- Nếu file chưa có → fetch live từ `product-service` và build tạm
- RRF merge sparse + dense → top-K sản phẩm liên quan

### 4.7.6 Bước 5 — GraphRAG mở rộng ngữ cảnh

`GraphRepository.get_context(customer_id, product_id)` thêm cạnh behavior, category. Neo4j pipeline (khi bật) walk từ User node → Product đã tương tác → sản phẩm cùng category.

### 4.7.7 Bước 6 — Recommendation Engine

Trang chủ customer: `_recommendation_order_ids()` → `GET recommender/recommendations/{entity_id}/`.

`RecommenderService.recommend()`:
- Đọc behavior matrix từ `recommender_db`
- Gọi `order-service/orders/internal/recommender-orders/` cho co-purchase
- Kết hợp weighted score → sort → `recommended_product_ids`

Gateway `_customer_recommendation_products_page()` paginate theo thứ tự score; fallback newest nếu AI trả rỗng.

### 4.7.8 Bước 7 — Kết quả hiển thị

Template `home.html` nhận `recommendation_products` đã `_fmt_product`. Infinite scroll gọi `GET /api/home/products/?page=2` — vẫn theo thứ tự recommendation.

### 4.7.9 Sequence Diagram — Tích hợp gợi ý trang chủ

```mermaid
sequenceDiagram
    participant U as Customer
    participant GW as api-gateway
    participant PROD as product-service
    participant REC as recommender-ai-service
    participant ORD as order-service

    U->>GW: GET /
    GW->>PROD: GET /products/?flash_sale=true
    GW->>REC: GET /recommendations/{customer_id}/
    REC->>ORD: GET /orders/internal/recommender-orders/
    REC-->>GW: recommended_product_ids + scores
    GW->>PROD: GET /products/{id} (hydrate batch)
    GW-->>U: HTML home + AI-ordered products
```

### 4.7.10 Activity Diagram — Hành vi mua hàng → AI

```mermaid
flowchart TD
    Start([Customer thêm giỏ]) --> T1[track_behavior add_to_cart]
    T1 --> Checkout[Checkout POST]
    Checkout --> Order[order-service tạo đơn]
    Order --> Pay{Thanh toán COD?}
    Pay -->|Yes| T2[track_order_purchases purchase]
    T2 --> Rec[recommender cập nhật matrix]
    Rec --> Neo[recommender-consumer Neo4j edge]
    Pay -->|Mock| Callback[payment_callback]
    Callback --> T2
```

### Nhận xét mục 4.7

AI được tích hợp **không xâm lấn** luồng commerce: checkout vẫn chạy nếu recommender down (fallback sản phẩm mới nhất). Đây là thiết kế **resilient** phù hợp production thực tế."""

SEC_48 = r"""## 4.8 TRIỂN KHAI KNOWLEDGE BASE

### 4.8.1 Dữ liệu lấy từ đâu

Nguồn chính: **product-service** — toàn bộ sản phẩm active qua REST `GET /products/?page_size=500+`.

Mỗi document gồm: `name`, `description`, `sku`, `category.name`, `brand.name`, `attributes` — ghép trong `_product_doc()`:

```python
# hybrid_retriever.py
parts = [raw.get("name"), raw.get("description"), raw.get("sku"), cat_name, brand_name]
return _tokenize_vi(" ".join(parts))
```

### 4.8.2 Tiền xử lý

- Lowercase, giữ dấu tiếng Việt
- Loại ký tự đặc biệt regex
- Chuẩn hóa khoảng trắng `_tokenize_vi()`

### 4.8.3 Chunking

Catalog e-commerce mỗi sản phẩm = **1 document** (không chunk paragraph dài như tài liệu PDF). Lý do: mỗi SKU là đơn vị retrieval tự nhiên.

### 4.8.4 Embedding

- Model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (env `EMBEDDING_MODEL`)
- Encode toàn bộ `docs[]` → matrix `embeddings` numpy
- Optional TruncatedSVD giảm chiều

### 4.8.5 Indexing

Command: `python manage.py build_catalog_index`

Output: `recommender-ai-service/rag/catalog_hybrid_index.pkl` chứa:
- `catalog`, `docs`, `product_ids`
- `_tfidf`, `_tfidf_matrix`
- `_embeddings`

Load lúc runtime: `HybridProductRetriever._ensure_index()` — đọc pickle vào RAM.

### 4.8.6 Dữ liệu lưu ở đâu

| Lớp | Vị trí | Ghi chú |
|-----|--------|---------|
| Source of truth | `product_db` PostgreSQL | CRUD sản phẩm |
| KB index file | `catalog_hybrid_index.pkl` | Cần rebuild khi catalog đổi nhiều |
| Runtime cache | RAM process recommender | Mất khi restart container |

**ChromaDB / FAISS file:** Không tìm thấy trong source code.

### Nhận xét mục 4.8

KB triển khai **đơn giản, hiệu quả** cho catalog có cấu trúc. Trade-off: phải chạy `build_catalog_index` sau khi import sản phẩm mới hàng loạt."""

SEC_49 = r"""## 4.9 TRIỂN KHAI GRAPH DATABASE

### 4.9.1 Neo4j trong Docker

`docker-compose.yml` service `neo4j`:
- Bolt: `bolt://neo4j:7687`
- Auth: env `NEO4J_AUTH`
- Volume: `neo4j_data`

Consumer `recommender-consumer` lắng nghe RabbitMQ, ghi node/edge khi có event mua hàng, view...

### 4.9.2 Knowledge Graph — schema

**Node types** (từ `graph/schema.py` và Neo4j pipeline):
- `User` — `customer_id`
- `Product` — `product_id`
- `Category` — `category_id`

**Relationship types:**
- `(Product)-[:BELONGS_TO]->(Category)`
- `(User)-[:INTERACTED {action, weight}]->(Product)`

### 4.9.3 graph_kb.json (GraphRAG offline)

`GraphRepository` lưu JSON tại `data/graph_kb.json` (env `GRAPH_KB_PATH`):

```python
# Khi ghi behavior
self._upsert_node(nodes, GraphNode(u, "User", {"customer_id": customer_id}))
self._upsert_node(nodes, GraphNode(p, "Product", {"product_id": product_id}))
self._upsert_edge(edges, GraphEdge(u, p, action, weight, {}))
```

Dùng cho RAG context string: `"graph: direct behavior weight=2.50"`.

### 4.9.4 Cypher Query — ví dụ thực tế

Truy vấn candidate từ user đã mua sản phẩm cùng category:

```cypher
MATCH (u:User {customer_id: $customer_id})-[r:INTERACTED]->(p:Product)-[:BELONGS_TO]->(c:Category)
MATCH (p2:Product)-[:BELONGS_TO]->(c)
WHERE NOT (u)-[:INTERACTED]->(p2)
RETURN p2.product_id AS product_id, count(*) AS score
ORDER BY score DESC
LIMIT 20
```

*(Pattern tương đương logic trong `recommendation_pipeline.py` — cần đối chiếu file khi debug.)*

### 4.9.5 GraphRAG trong chat

`rag_llm.py` kết hợp:
- Retrieval text từ hybrid index
- Graph context từ `GraphRepository` hoặc NetworkX fallback
- Đưa vào prompt Groq → câu trả lời có tham chiếu sản phẩm liên quan

### Nhận xét mục 4.9

Hệ thống dùng **hai store graph**: JSON nhẹ cho RAG, Neo4j cho recommendation pipeline async. Không bắt buộc một công nghệ duy nhất."""

SEC_410 = r"""## 4.10 TRIỂN KHAI RECOMMENDATION SYSTEM

### 4.10.1 Tổng quan pipeline

```mermaid
flowchart LR
    UB[User Behavior events] --> FE[Feature Extraction]
    FE --> EM[Embedding / CF matrix]
    EM --> GR[GraphRAG Neo4j candidates]
    GR --> RM[RecommenderService hybrid]
    RM --> RK[Ranking weighted score]
    RK --> TN[Top-N product IDs]
    TN --> HY[Hydrate product-service]
    HY --> UI[home.html / recommendations page]
```

### 4.10.2 Dữ liệu đầu vào

| Nguồn | Loại dữ liệu | Cách thu thập |
|-------|--------------|---------------|
| Behavior events | view, cart, wishlist, purchase | `track_behavior()` → `POST /api/recommender/events/` |
| Order history | co-purchase pairs | `GET /orders/internal/recommender-orders/` |
| Product catalog | category, price, stock | `ProductCatalog` sync từ product-service |
| Graph | user-product edges | Neo4j + `graph_kb.json` |

Trọng số hành vi (`behavior_actions.DEFAULT_ACTION_WEIGHTS`):
- `purchase` cao nhất
- `add_to_cart`, `wishlist` trung bình
- `view`, `click` thấp hơn

### 4.10.3 Feature Extraction

`RecommenderRepository` aggregate events thành sparse matrix user×item×action.

`implicit_cf_engine` train ALS trên matrix — command `train_implicit_cf_local`.

`behavior_prediction_service` (BiLSTM) dự đoán **next action** — ảnh hưởng strategy string trả về API.

### 4.10.4 Embedding

- CF: latent factors từ ALS/NMF
- Content: category affinity khi user thích category X
- Không embedding user profile riêng — dùng id + behavior history

### 4.10.5 GraphRAG trong recommendation

`RecommendationPipeline._retrieve_candidates_neo4j(user_id)` bổ sung candidate ngoài CF — đặc biệt khi user ít behavior (warm graph từ user tương tự).

### 4.10.6 Recommendation Model — logic đề xuất

```python
# recommender_service.py — ý tưởng hybrid
# 1. CF scores từ implicit engine
# 2. Co-occurrence từ users có hành vi giống
# 3. Co-purchase từ orders
# 4. Category affinity
# 5. Fallback popular by category
```

Trọng số cấu hình env: `IMPLICIT_CF_ALS_WEIGHT`, `COOCCURRENCE_WEIGHT`, `COPURCHASE_WEIGHT`, `CATEGORY_AFFINITY_WEIGHT`.

### 4.10.7 Ranking

Mỗi `product_id` nhận **tổng điểm weighted**. Sort giảm dần. Loại sản phẩm hết hàng / inactive qua `ProductCatalog`.

API trả về:
```json
{
  "recommended_product_ids": [12, 45, 7],
  "recommendation_scores": [{"product_id": 12, "score": 8.42}],
  "strategy": "hybrid_cf_graph",
  "next_action_prediction": {"action": "add_to_cart", "confidence": 0.71}
}
```

### 4.10.8 Top-N Products — gateway

`_recommendation_order_ids(request, customer_id, limit)` cache ngắn, gọi recommender, trả list id.

Trang `/recommendations/` render full list. Admin `/admin/recommendation/` xem metrics/offline eval.

### 4.10.9 Cold start

- **Guest:** không gọi recommender — sản phẩm `sort_by=newest`
- **Customer mới:** category-weighted popular + trending API `GET /api/v1/recommendations/trending`

### Nhận xét mục 4.10

Recommendation là **hybrid thực dụng** — không phụ thuộc một model duy nhất. Có thể giải thích từng layer khi bảo vệ đồ án."""

SEC_411 = r"""## 4.11 TRIỂN KHAI CHATBOT

### 4.11.1 Chat UI

Widget embed trong template base — `chatbot-widget.js` / CSS từ `recommender-ai-service/static/` hoặc copy vào gateway static.

UI gồm:
- Bubble icon góc màn hình
- Panel chat lịch sử `history[]` lưu phía client (sessionStorage)
- Gửi `POST /ai/chat/` same-origin

### 4.11.2 Backend API (BFF proxy)

Không expose trực tiếp port 8011 ra browser. Gateway `ai_chat_proxy`:
- `@csrf_exempt` + `@require_POST`
- Forward body JSON nguyên vẹn
- Retry connection 3 lần, timeout 90s

### 4.11.3 AI Service

`KTMPChatConsultingView` → `rag_llm.chat(user_id, message, history, recent_behaviors)`:
1. Intent classification
2. Retrieve products
3. Build prompt tiếng Việt
4. Groq completion
5. Parse response + attach product cards

### 4.11.4 Knowledge Base trong chat

Mỗi câu hỏi tư vấn SP kích hoạt `HybridProductRetriever.retrieve(message, top_k=5)`.

Context đưa vào LLM gồm tên, giá, mô tả rút gọn 280 ký tự, category.

### 4.11.5 Cách chatbot sinh câu trả lời

Prompt template trong `rag_llm.py` yêu cầu:
- Trả lời tiếng Việt tự nhiên
- Chỉ dùng thông tin context (giảm hallucination)
- Gợi ý product_id cụ thể khi phù hợp

Output field `products` cho frontend render thumbnail + link `/products/{id}/`.

### 4.11.6 Sequence — một vòng chat

```mermaid
sequenceDiagram
    participant UI as chatbot-widget.js
    participant GW as /ai/chat/
    participant REC as chat-ktmp
    participant RAG as HybridRetriever
    participant LLM as Groq

    UI->>GW: POST {message, user_id, history}
    GW->>REC: proxy
    REC->>RAG: retrieve(message)
    RAG-->>REC: context docs
    REC->>LLM: chat completion
    LLM-->>REC: answer
    REC-->>GW: {answer, products, intent}
    GW-->>UI: JSON
    UI->>UI: render bubbles + product cards
```

### Nhận xét mục 4.11

Chatbot **Mochi/KTMP** là điểm chạm AI trực tiếp với khách. Proxy BFF giải quyết CORS và che API key Groq phía server."""

SEC_412 = r"""## 4.12 TRIỂN KHAI HỆ THỐNG BẰNG DOCKER

### 4.12.1 Docker Architecture

Toàn bộ hệ thống chạy bằng một lệnh `docker-compose up` từ root repo. Mạng chung `ecommerce-net` — mọi container resolve tên service (DNS nội bộ).

### 4.12.2 Deployment Diagram

```mermaid
flowchart TB
    subgraph Host
        subgraph Compose[docker-compose]
            NG[nginx:80]
            GW[api-gateway:8000]
            subgraph MS[Microservices x14]
                AUTH[auth-service]
                PROD[product-service]
                ORD[order-service]
                REC[recommender-ai-service:8011]
            end
            subgraph Data
                PG[(PostgreSQL x14)]
                N4J[(neo4j)]
                RD[(redis)]
                MQ[rabbitmq]
            end
            subgraph Workers
                OW[order-outbox-worker]
                PC[payment-consumer]
                RC[recommender-consumer]
            end
        end
    end
    User((User)) --> NG
    NG --> GW
    GW --> MS
    MS --> Data
    MS --> MQ
    MQ --> Workers
    Workers --> REC
    Workers --> N4J
```

### 4.12.3 Container Structure — nhóm vai trò

| Nhóm | Containers | Vai trò |
|------|------------|---------|
| Edge | `nginx` | Public entry :80 |
| BFF | `api-gateway` | Storefront + orchestration |
| Core | `auth`, `user`, `product`, `cart`, `order`, `payment`, `shipping`, `promotion`, `interaction` | Business API |
| v2 | `catalog`, `inventory`, `notification` | SAGA / mở rộng |
| AI | `recommender-ai-service`, `neo4j`, `model-serving-service` | ML + graph |
| Data | `*-db` x14, `redis`, `rabbitmq` | Persistence + messaging |
| Workers | `*-consumer`, `*-outbox-worker` | Async processing |
| Observability | `jaeger` | Tracing (optional) |

### 4.12.4 Volume

Mỗi PostgreSQL có named volume (`product_db_data`, `order_db_data`...) — dữ liệu survive `docker-compose down` (không `-v`).

Neo4j: `neo4j_data`, `neo4j_logs`, `neo4j_import`.

### 4.12.5 Network

Tất cả attach `ecommerce-net`. Service gọi nhau qua hostname: `http://product-service:8000/products/`.

Chỉ `nginx` expose port 80 ra host (và một số DB port debug 55432+).

### 4.12.6 Environment Variables

Ví dụ quan trọng từ compose:
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DB_NAME_*`
- `INTERNAL_TOKEN`, `INTERNAL_SIGNING_SECRET` — service-to-service
- `GROQ_API_KEY` — recommender chat
- `NEO4J_AUTH` — graph DB
- `RABBITMQ_DEFAULT_USER/PASS`

`api-gateway` `SERVICE_URLS` map tên → URL nội bộ trong `settings.py`.

### 4.12.7 Giao tiếp giữa containers

1. **Sync HTTP:** gateway → microservices (requests)
2. **Async AMQP:** outbox worker publish → consumer xử lý
3. **Health:** mỗi service `/health/live`, `/health/ready` cho depends_on

### Nhận xét mục 4.12

Docker Compose phù hợp demo và phát triển đồ án. Production thật cần Kubernetes + secret manager — **không có trong repo**."""

SEC_413 = r"""## 4.13 TRIỂN KHAI API

Phần này liệt kê API **thực tế trong source code**, nhóm theo service. Storefront chủ yếu gọi qua BFF; bảng gồm cả REST gốc để đối chiếu.

### 4.13.1 api-gateway — JSON / proxy (storefront gọi trực tiếp)

| Method | Endpoint | Chức năng | Input | Output | Auth |
|--------|----------|-----------|-------|--------|------|
| GET | `/api/guest/products/` | Infinite scroll guest | `page`, `page_size` | `{products[], has_more}` | Guest only |
| GET | `/api/home/products/` | Infinite scroll customer AI order | `page`, `page_size` | `{products[], total_pages}` | Customer JWT session |
| POST | `/ai/chat/` | Proxy chatbot | `{message, user_id, history}` | `{answer, products, intent}` | Không (csrf_exempt) |
| GET | `/orders/api/status/` | Poll trạng thái đơn AJAX | `order_ids` | status map | Session |
| GET | `/addresses/api/` | JSON địa chỉ profile | — | address list | Session |
| POST | `/cart/{id}/checkout/apply-voucher/` | Áp voucher | `promotion_code` | discount info | Customer |
| GET | `/cart/{id}/checkout/shipping-fees/` | Phí ship theo city | `city`, `method_id` | `{shipping_fee}` | Customer |

### 4.13.2 auth-service

| Method | Endpoint | Chức năng | Input | Output | Auth |
|--------|----------|-----------|-------|--------|------|
| POST | `/auth/register/` | Đăng ký | username, email, password, phone, role | JWT + user | Public |
| POST | `/auth/login/` | Đăng nhập | username, password, role | JWT + user | Public, rate limit IP |
| POST | `/auth/refresh/` | Refresh token | refresh | access mới | Refresh token |
| GET | `/auth/introspect/` | Validate JWT | Header Authorization | `{active: true}` | NGINX auth_request |

**Validation:** `RegisterSerializer`, `LoginSerializer` — DRF validate field required, email format.

### 4.13.3 product-service (storefront catalog)

| Method | Endpoint | Chức năng | Input | Output | Auth |
|--------|----------|-----------|-------|--------|------|
| GET | `/products/` | Danh sách SP | `page`, `category_id`, `sort_by`, `flash_sale` | Paginated products | Public/internal |
| GET | `/products/{id}/` | Chi tiết SP | pk | Product + category + brand | Public |
| GET | `/categories/` | Danh mục | page_size | Categories | Public |
| POST | `/internal/reserve-stock/` | Giữ hàng đặt đơn | order_id, items[] | reservation result | Internal HMAC |

### 4.13.4 cart-service

| Method | Endpoint | Chức năng | Input | Output | Auth |
|--------|----------|-----------|-------|--------|------|
| GET | `/carts/{customer_id}/` | Xem giỏ | customer_id | cart + items | JWT forwarded |
| POST | `/carts/{customer_id}/items/` | Thêm SP | product_id, quantity, variant_id | item | Customer |
| PUT | `/carts/{customer_id}/items/{item_id}/` | Đổi SL | quantity | item | Customer |
| DELETE | `/carts/{customer_id}/` | Xóa giỏ sau checkout | — | 204 | Internal |

### 4.13.5 order-service (legacy — BFF dùng)

| Method | Endpoint | Chức năng | Input | Output | Auth |
|--------|----------|-----------|-------|--------|------|
| POST | `/orders/` | Tạo đơn | customer_id, items[], shipping_address, promotion_code | Order id | Customer |
| GET | `/orders/{id}/` | Chi tiết đơn | pk | Order + items | Owner/staff |
| GET | `/orders/internal/recommender-orders/` | Lịch sử mua cho AI | customer_id? | orders[] | Internal |

### 4.13.6 payment-service (legacy)

| Method | Endpoint | Chức năng | Input | Output | Auth |
|--------|----------|-----------|-------|--------|------|
| GET | `/payment-methods/` | PT thanh toán | — | COD, VNPay Mock... | Auth |
| POST | `/payments/` | Ghi thanh toán | order_id, payment_amount, payment_method_id | Payment | Customer |

### 4.13.7 shipping-service

| Method | Endpoint | Chức năng | Input | Output | Auth |
|--------|----------|-----------|-------|--------|------|
| GET | `/api/methods/` | PT vận chuyển | — | methods[] | Public |
| POST | `/api/shipping/calculate-fee/` | Tính phí | items[], city, method_id | fee, distance_km | Public |

### 4.13.8 promotion-service

| Method | Endpoint | Chức năng | Input | Output | Auth |
|--------|----------|-----------|-------|--------|------|
| POST | `/api/promotions/apply-voucher/` | Kiểm tra voucher | code, cart_total | discount | Gateway checkout |
| GET | `/api/promotions/flash-sale-prices/` | Giá flash sale | product_ids | price map | Internal |

### 4.13.9 interaction-service

| Method | Endpoint | Chức năng | Input | Output | Auth |
|--------|----------|-----------|-------|--------|------|
| POST | `/api/v1/interactions/interactions/` | Ghi event | user_id, product_id, event_type | 201 | Public/API |
| GET, POST | `/api/v1/interactions/reviews/` | Đánh giá SP | rating, comment | Review | Customer |
| GET, POST | `/api/v1/interactions/wishlists/` | Wishlist | product_id | entry | Customer |
| GET, POST | `/api/v1/interactions/tickets/` | Support ticket | subject, message | ticket | Customer |

### 4.13.10 recommender-ai-service

| Method | Endpoint | Chức năng | Input | Output | Auth |
|--------|----------|-----------|-------|--------|------|
| GET | `/recommendations/{customer_id}/` | Gợi ý hybrid | limit query | ids + scores + strategy | Optional headers |
| POST | `/api/recommender/events/` | Behavior event | customer_id, product_id, action | 201 | X-Entity-Id header |
| POST | `/api/recommender/chat-ktmp` | Chat RAG | message, user_id, history | answer, products | Public nội mạng |
| GET | `/api/recommender/next-action/{customer_id}/` | Dự đoán hành vi | — | action, confidence | Internal |
| GET | `/api/v1/recommendations/trending` | SP trending | — | product ids | Public |

### 4.13.11 Phân tích chung — Authentication giữa services

Gateway forward JWT qua helper `_auth_headers(request)`:
- `Authorization: Bearer {access_token}` từ session
- `X-User-Id`, `X-Entity-Id`, `X-Roles`

Service nội bộ dùng `common.auth.require_internal` + HMAC `X-Service-Signature`.

### 4.13.12 Validation điển hình

| Layer | Ví dụ |
|-------|-------|
| Gateway form | checkout: bắt buộc `address_id`, `shipping_method_id` |
| DRF Serializer | order checkout SAGA: `CheckoutRequestSerializer` |
| Business | payment: amount > 0, order tồn tại |
| AI | chat: `message` không rỗng → 400 |

### Nhận xét mục 4.13

API surface lớn do microservice — BFF che bớt complexity cho frontend. Khi debug, trace từ `gateway/urls.py` → `views.py` → `SERVICE_URLS` endpoint tương ứng."""




