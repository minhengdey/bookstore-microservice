# -*- coding: utf-8 -*-
"""Chapter 4 section bodies — re-exports all sections."""

from build_chapter4_core import (
    SEC_42, SEC_43, SEC_44, SEC_45, SEC_46, SEC_47,
    SEC_48, SEC_49, SEC_410, SEC_411, SEC_412, SEC_413,
)
from build_chapter4_ui import SEC_414
from build_chapter4_eval import SEC_415, SEC_416

# 4.1 defined here (overview)
SEC_41 = r"""## 4.1 TỔNG QUAN QUÁ TRÌNH XÂY DỰNG HỆ THỐNG

### 4.1.1 Mục tiêu triển khai

Đồ án không dừng ở thiết kế trên giấy (Chương 2) và thiết kế AI (Chương 3) mà **hiện thực hóa** thành hệ thống chạy được bằng `docker-compose up`. Mục tiêu cụ thể:

| STT | Mục tiêu | Cách đo lường trong dự án |
|-----|----------|---------------------------|
| M1 | Khách hàng mua hàng end-to-end | Đăng ký → xem SP → giỏ → checkout → thanh toán → theo dõi đơn |
| M2 | Microservice độc lập | Mỗi domain có DB riêng, deploy container riêng |
| M3 | Bảo mật xuyên service | JWT + HMAC nội bộ (`common/auth.py`) |
| M4 | AI tích hợp storefront | Gợi ý trang chủ, chatbot Mochi, behavior tracking |
| M5 | Vận hành async | RabbitMQ outbox: payment → shipping, events → AI |
| M6 | Mở rộng SAGA v2 | `catalog-service` + `inventory-service` (song song legacy) |

### 4.1.2 Các thành phần hệ thống sau khi hoàn thiện

```mermaid
flowchart TB
    subgraph Client
        BR[Trình duyệt]
    end
    subgraph Edge
        NG[NGINX :80]
    end
    subgraph BFF
        GW[api-gateway Django :8000]
    end
    subgraph CoreMS[Microservices]
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
    subgraph AI[AI Layer]
        REC[recommender-ai-service]
        N4J[(Neo4j)]
        MS[model-serving mock]
    end
    subgraph Data[Data Layer]
        PG[(PostgreSQL x14)]
        RD[(Redis)]
        MQ[RabbitMQ]
    end
    BR --> NG --> GW
    GW --> CoreMS
    GW --> REC
    REC --> N4J
    REC --> PROD
    CoreMS --> PG
    CoreMS --> MQ
    GW --> RD
```

### 4.1.3 Phạm vi triển khai

**Trong phạm vi đồ án (có trong repo):**
- Storefront Django Templates qua `api-gateway` (không SPA React)
- Luồng đặt hàng **legacy** qua `order-service/orders/` + `product-service/reserve-stock`
- Thanh toán MOCK/COD qua `payment-service`
- AI: hybrid recommender + RAG chatbot + Neo4j event sync
- Portal Staff (`/staff/`) và Admin (`/admin/`)

**Ngoài phạm vi / chưa hoàn thiện:**
- Checkout SAGA v2 trên BFF (code có, storefront chưa gọi)
- OAuth Google/Facebook, OTP, quên mật khẩu
- Payment gateway thật VNPay/MoMo
- Kubernetes production
- **React/Next.js:** Không tìm thấy trong source code dự án

### 4.1.4 Vai trò từng lớp — giải thích dễ hiểu

| Thành phần | Vai trò (nói đơn giản) | Thư mục / container |
|------------|------------------------|-------------------|
| **Frontend** | Giao diện HTML user nhìn thấy | `api-gateway/templates/`, `static/` |
| **Backend API** | 14 service xử lý nghiệp vụ | `*-service/` |
| **BFF** | "Người phiên dịch" — gom nhiều API thành 1 trang | `api-gateway/gateway/` |
| **Database** | Mỗi service 1 DB PostgreSQL riêng | `*-db` containers |
| **AI Service** | Gợi ý + chat | `recommender-ai-service` |
| **Knowledge Base** | Catalog text cho chatbot | `catalog_hybrid_index.pkl` |
| **Vector index** | Embedding tìm kiếm semantic | pickle in-memory (**không ChromaDB**) |
| **Neo4j** | Đồ thị user–product | container `neo4j` |
| **Recommendation Engine** | `RecommenderService` hybrid | Python in-process |
| **LLM** | Groq API sinh câu trả lời | `rag/rag_llm.py` |

### 4.1.5 Quy trình xây dựng theo giai đoạn

1. **Giai đoạn 1 — Hạ tầng:** `docker-compose.yml`, PostgreSQL, Redis, RabbitMQ, `common/`.
2. **Giai đoạn 2 — Core commerce:** auth → user → product → cart → order → payment → shipping.
3. **Giai đoạn 3 — BFF:** `api-gateway` templates + proxy REST nội bộ.
4. **Giai đoạn 4 — Mở rộng:** promotion, interaction, notification (code), catalog/inventory v2.
5. **Giai đoạn 5 — AI:** recommender-ai-service, Neo4j, chatbot widget, behavior tracking.
6. **Giai đoạn 6 — Edge:** NGINX rate limit, auth_request introspect.

### 4.1.6 Liên kết Chương 2 và Chương 3 với triển khai

| Thiết kế (Chương 2–3) | Triển khai thực tế (Chương 4) |
|------------------------|-------------------------------|
| Microservice architecture | 14 service + workers trong compose |
| API Gateway pattern | `api-gateway` Django BFF |
| RAG + GraphRAG | `hybrid_retriever.py` + `GraphRepository` + Neo4j |
| Hybrid recommender | `RecommenderService` 5 chiến lược |
| Event-driven | RabbitMQ consumers |
| Docker deployment | `docker-compose.yml` đầy đủ |

### Nhận xét mục 4.1

Chương 4 mô tả **hệ thống thật đang chạy**, không phải kiến trúc lý tưởng. Hai luồng order (legacy + SAGA) cùng tồn tại — cần nêu rõ khi bảo vệ."""
