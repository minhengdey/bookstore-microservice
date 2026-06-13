# -*- coding: utf-8 -*-
"""Section bodies for Chapter 3 generator."""

SEC_31 = r"""## 3.1 PHÂN TÍCH YÊU CẦU AI-SERVICE

AI-Service trong đồ án không phải một lớp "gắn thêm" vào website mà là **microservice độc lập** `recommender-ai-service` (Django REST, cổng **8011**), chịu trách nhiệm thu thập hành vi, dự đoán hành động tiếp theo, gợi ý sản phẩm và vận hành chatbot tư vấn **Mochi**. Mọi mô tả dưới đây bám file cấu hình `docker-compose.yml` (service `recommender-ai-service`, `neo4j`, `recommender-consumer`, `model-serving-service`) và mã nguồn thực tế.

### 3.1.1 Bài toán thực tế

Hệ thống E-Commerce của đồ án (`api-gateway` + 14 microservice) đã có đủ chức năng mua bán cơ bản, nhưng khi quy mô catalog tăng (mặc định `MOCK_PRODUCT_COUNT=320` sản phẩm, có thể mở rộng qua `product-service`), người dùng gặp các khó khăn sau — và mã nguồn AI-Service được xây dựng để giải quyết từng khó khăn cụ thể:

#### (1) Khó khăn khi người dùng tìm kiếm sản phẩm

Người dùng thường mô tả nhu cầu bằng ngôn ngữ tự nhiên ("tìm son môi giá rẻ cho da khô") trong khi `product-service` chỉ cung cấp API REST phân trang `GET /products/`. Tìm kiếm từ khóa đơn giản không hiểu ngữ cảnh, không gợi ý theo lịch sử duyệt web.

**Giải pháp trong source code:** lớp `HybridProductRetriever` (`rag/hybrid_retriever.py`) kết hợp **TF-IDF sparse** + **Sentence Transformer dense** + **RRF fusion** để truy xuất sản phẩm theo câu hỏi tự nhiên; chatbot `RAGChatLLM` (`rag/rag_llm.py`) gọi retriever này trước khi đưa ngữ cảnh cho LLM.

#### (2) Vấn đề quá nhiều sản phẩm (Information Overload)

Khi catalog có hàng trăm/thousands SKU, người dùng chỉ thấy danh sách phân trang hoặc sản phẩm phổ biến — các sản phẩm "đuôi dài" (long-tail) khó được khám phá.

**Giải pháp trong source code:** `RecommenderService` (`app/services/recommender_service.py`) dùng **6 tầng scoring hybrid** (Matrix CF NMF, co-occurrence, co-purchase, category affinity, global popularity, item CF popularity) để xếp hạng cá nhân hóa; `RAGSystem.recommend_products()` (`rag/retriever.py`) có cơ chế **anti super-node** (lọc sản phẩm quá phổ biến ở percentile 95) để đa dạng hóa gợi ý.

#### (3) Vấn đề thông tin sản phẩm phân tán

Thông tin sản phẩm nằm ở `product-service` (tên, mô tả, giá, category, brand), hành vi ở `interaction-service` / `BehaviorEvent`, đơn hàng ở `order-service`, khuyến mãi ở `promotion-service`. Không có một nơi duy nhất để chatbot "đọc hiểu" toàn bộ.

**Giải pháp trong source code:** pipeline xây **Knowledge Base** (mục 3.3): `build_catalog_index` command lấy toàn bộ sản phẩm từ `product-service`, biến thành document text; `EventHandler` đồng bộ sự kiện vào PostgreSQL `recommender_db`, Redis sequence và Neo4j graph.

#### (4) Vấn đề chăm sóc khách hàng thủ công

Staff portal (`api-gateway/templates/staff/`) có ticket support nhưng không scale khi số lượng câu hỏi lặp lại ("chính sách đổi trả?", "sản phẩm này còn hàng không?") tăng cao.

**Giải pháp trong source code:** Chatbot **Mochi** qua `POST /api/recommender/chat-ktmp` → proxy `api-gateway` `POST /ai/chat/` (`gateway/views.py` → `ai_chat_proxy`). Intent router (`rag/intent_router.py`) phân loại `POLICY`, `SEARCH`, `RECOMMEND`, … để trả lời chính sách hoặc gợi ý sản phẩm tự động.

#### (5) Vấn đề đề xuất sản phẩm chưa cá nhân hóa

Khách mới (cold start) và khách có lịch sử đều cần trải nghiệm khác nhau. Hệ thống chỉ sort theo giá hoặc mới nhất không đủ.

**Giải pháp trong source code:**
- **Cold start:** `RecommenderService.recommend()` trả `strategy="random-cold-start"` — xáo trộn có seed theo `customer_id`.
- **Có lịch sử:** Matrix CF + behavior scores từ `BehaviorEvent` + **BiLSTM next-action** điều chỉnh `behavior_bias` (mục 3.8, 3.13).
- **Graph:** Neo4j lưu quan hệ `User-[PURCHASED|VIEW|ADDED_TO_CART]->Product` realtime (`event_handler.py`).

#### Bảng ánh xạ bài toán → công nghệ AI trong dự án

| Bài toán | Công nghệ triển khai | File / Service chính |
|----------|---------------------|----------------------|
| Tư vấn tự nhiên | Chatbot + Groq LLM | `rag/rag_llm.py`, `GROQ_MODEL=llama-3.1-8b-instant` |
| Tìm kiếm thông minh | Hybrid Retrieval (TF-IDF + Embedding) | `rag/hybrid_retriever.py` |
| Gợi ý cá nhân | Hybrid Recommender + NMF + BiLSTM bias | `app/services/recommender_service.py` |
| Hiểu ngữ cảnh hội thoại | Intent Router + history 10 turns | `rag/intent_router.py`, `call_groq()` |
| Khai thác tri thức sản phẩm | Knowledge Base index | `build_catalog_index`, `catalog_hybrid_index.pkl` |
| Quan hệ phức tạp user–product | Graph (Neo4j + NetworkX) | `event_handler.py`, `rag/retriever.py` |
| Bổ sung tri thức cho LLM | RAG | `RAGChatLLM.chat()` |
| Mở rộng ngữ cảnh theo đồ thị | GraphRAG (kết hợp graph + retrieval) | `RAGSystem` + Neo4j candidates |
| Dự đoán hành vi | Deep Learning BiLSTM | `inference_utils.py`, `model_best.keras` |

**Lưu ý trung thực với source code:**
- **Elasticsearch / Kafka cho AI:** Không tìm thấy trong source code dự án.
- **OpenAI / Anthropic API:** Có trong `requirements.txt` nhưng **không được import** trong mã nguồn; production dùng **Groq**.
- **ChromaDB / Pinecone / Milvus:** Không tìm thấy trong source code dự án.

### 3.1.2 Mục tiêu của AI-Service

Dựa trên các endpoint và service class hiện có, mục tiêu của `recommender-ai-service` được cụ thể hóa như sau:

| STT | Mục tiêu nghiệp vụ | Cách đo lường trong hệ thống | Thành phần thực hiện |
|-----|---------------------|------------------------------|----------------------|
| M1 | Trả lời câu hỏi khách hàng bằng tiếng Việt | `POST /api/recommender/chat-ktmp` trả `answer`, `products`, `intent` | `RAGChatLLM`, Groq LLM |
| M2 | Tìm kiếm sản phẩm theo mô tả tự nhiên | `hybrid_search()` trả top-K sản phẩm khớp query | `HybridProductRetriever` |
| M3 | Đề xuất sản phẩm cá nhân hóa | `GET /recommendations/<customer_id>/` | `RecommenderService` |
| M4 | Hiểu ngữ cảnh hội thoại đa lượt | `history` tối đa 10 turns trong `call_groq()` | `rag_llm.py` |
| M5 | Tư vấn mua hàng (gợi ý + giải thích) | Prompt ghép `suggested_products`, `next_action_prediction` | `RAGChatLLM.chat()` |
| M6 | Khai thác dữ liệu sản phẩm tập trung | Index rebuild từ `product-service` | `build_catalog_index` |
| M7 | Hỗ trợ ra quyết định (next action) | `GET /api/recommender/next-action/<id>/` | `BehaviorPredictionService` |
| M8 | Ghi nhận hành vi realtime | `POST /api/recommender/events/` + RabbitMQ consumer | `BehaviorEventView`, `consume_events` |
| M9 | A/B test và MLOps (hướng mở rộng) | `GET /api/v1/recommendations/personal` | `RecommendationPipeline` |

**Giải thích mục tiêu M7 — tại sao "next action" quan trọng:**

Khi BiLSTM dự đoán người dùng sắp `purchase` với confidence cao, `RecommenderService._behavior_bias()` **tăng** trọng số gợi ý (hệ số +0.25 × confidence). Nếu dự đoán `view`/`search`, bias **giảm** (−0.10), tránh ép mua khi người dùng chỉ đang duyệt. Đây là cầu nối giữa Deep Learning và Recommendation — không phải AI "trang trí".

```python
# app/services/recommender_service.py — logic behavior_bias (tóm tắt)
# purchase/add_to_cart → bias += confidence * 0.25 (max)
# view/click/search → bias -= confidence * 0.10
# clamp min 0.75
```

### Nhận xét mục 3.1

Phần 3.1 xác lập AI-Service không phải khái niệm trừu tượng mà là **bộ microservice có API, model artifact, pipeline dữ liệu và tích hợp UI cụ thể**. Các mục 3.2–3.14 sẽ đi sâu từng thành phần kỹ thuật."""

SEC_32 = r"""## 3.2 KIẾN TRÚC TỔNG THỂ AI-SERVICE

### 3.2.1 Vị trí AI-Service trong hệ thống E-Commerce

`recommender-ai-service` nằm song song với các domain service (auth, product, cart, order, …), giao tiếp qua:
- **HTTP nội bộ** (không qua NGINX edge cho service-to-service): `product-service`, `order-service`
- **HTTP qua api-gateway** (browser): proxy `/ai/chat/`, `/recommendations/<id>/`
- **RabbitMQ** (async): `recommender-consumer` chạy `manage.py consume_events`
- **PostgreSQL** riêng: `recommender_db`
- **Neo4j** + **Redis**: graph và sequence store

### 3.2.2 Sơ đồ kiến trúc tổng thể

```mermaid
flowchart TB
    subgraph Client["Người dùng / Trình duyệt"]
        U[User]
    end

    subgraph Frontend["Frontend — api-gateway"]
        FE[Django Templates + Static JS]
        CW[chatbot-widget.js]
        HS[home-storefront.js]
        BT[behavior_tracking.py]
    end

    subgraph Gateway["AI Gateway — lớp BFF"]
        AG[api-gateway :8000]
        PROXY["POST /ai/chat/"]
        REC_PROXY["GET /recommendations/"]
    end

    subgraph AISvc["recommender-ai-service :8011"]
        RV[recommender_views.py]
        RAGV[rag_views.py — KTMPChatConsultingView]
        RS[RecommenderService]
        BPS[BehaviorPredictionService]
        RAGLLM[RAGChatLLM]
        HPR[HybridProductRetriever]
        RAGSYS[RAGSystem — NetworkX]
        RP[RecommendationPipeline]
        EH[EventHandler]
    end

    subgraph LLM["LLM"]
        GROQ[Groq API — llama-3.1-8b-instant]
    end

    subgraph RAGEng["RAG Engine"]
        RET[TF-IDF + Sentence Transformer]
        RRF[RRF Fusion + Cross-Encoder Rerank]
    end

    subgraph GraphRAG["GraphRAG Engine"]
        NX[NetworkX Graph — rag_system.pkl]
        N4J[Neo4j — bolt://neo4j:7687]
    end

    subgraph Storage["Lưu trữ tri thức & vector"]
        PKL[catalog_hybrid_index.pkl]
        CSV[data_user500.csv]
        VEC[Embedding vectors in-memory]
    end

    subgraph KB["Knowledge Base"]
        CAT[Catalog từ product-service]
        BEH[BehaviorEvent PostgreSQL]
        PROJ[UserProjection / ProductProjection]
    end

    subgraph RecEng["Recommendation Engine"]
        CF[ImplicitCFEngine — NMF]
        HYB[6-layer Hybrid Scoring]
    end

    subgraph DL["Deep Learning Model"]
        BILSTM[BiLSTM + MultiHeadAttention]
        ART[model_best.keras + encoders.pkl]
    end

    subgraph EcomDB["E-Commerce Databases"]
        PG[(recommender_db)]
        PS[(product_db)]
        OS[(order_db)]
        RD[(Redis)]
    end

    U --> FE
    FE --> CW
    FE --> HS
    CW --> AG
    HS --> AG
    BT --> AG
    AG --> PROXY
    AG --> REC_PROXY
    PROXY --> RAGV
    REC_PROXY --> RV
    RAGV --> RAGLLM
    RAGLLM --> GROQ
    RAGLLM --> HPR
    RAGLLM --> RS
    RAGLLM --> RAGSYS
    HPR --> RET
    RET --> RRF
    RRF --> PKL
    RAGSYS --> NX
    RS --> CF
    RS --> BPS
    BPS --> BILSTM
    BILSTM --> ART
    RS --> HYB
    RP --> N4J
    RP --> RD
    EH --> N4J
    EH --> RD
    EH --> PG
    HPR --> CAT
    RS --> PS
    RS --> OS
    BPS --> BEH
    RV --> RS
```

**Giải thích sơ đồ (đọc từ trên xuống):**

1. **User → Frontend:** Người dùng tương tác trang `home.html`, `product_detail.html` qua `api-gateway`. Widget chat `chatbot-widget.js` (cả bản trong `api-gateway/static/` và `recommender-ai-service/static/`) gửi tin nhắn tới gateway, không gọi thẳng Groq từ browser (bảo mật API key).

2. **AI Gateway:** `api-gateway` đóng vai **Backend-for-Frontend**. Hàm `ai_chat_proxy` (`gateway/views.py`) forward body JSON `{message, user_id, history, recent_behaviors}` tới `RECOMMENDER_URL/api/recommender/chat-ktmp`, retry tối đa 3 lần, timeout 90 giây.

3. **LLM:** `call_groq()` trong `rag/rag_llm.py` gọi REST `https://api.groq.com/openai/v1/chat/completions`. Model mặc định `llama-3.1-8b-instant`. Khi thiếu `GROQ_API_KEY`, hệ thống dùng `_local_fallback_answer()` — không crash.

4. **RAG Engine:** Trước khi gọi LLM, `HybridProductRetriever.hybrid_search()` truy xuất sản phẩm liên quan. Đây là tầng **Retrieval** của RAG.

5. **GraphRAG Engine:** Hai nguồn đồ thị:
   - **NetworkX** (`RAGSystem`): đồ thị tĩnh từ `data_user500.csv`, dùng cho user ID kiểu `U001` (dataset).
   - **Neo4j**: đồ thị động cập nhật từ sự kiện thật qua `EventHandler._update_neo4j_graph()`.

6. **Vector / Index:** Không có ChromaDB. Vector embedding lưu trong `catalog_hybrid_index.pkl` (numpy array) và load vào RAM khi khởi động.

7. **Knowledge Base:** Tập hợp catalog text + behavior + projections. Command `build_catalog_index` chạy trong `entrypoint.sh` khi container start.

8. **Recommendation Engine:** `RecommenderService` là engine chính phục vụ UI. `RecommendationPipeline` là luồng MLOps phụ (Neo4j candidates → model-serving).

9. **Deep Learning:** `BehaviorPredictionService` load `model_best.keras` in-process (không qua model-serving hiện tại).

10. **E-Commerce DB:** `BehaviorEvent` lưu PostgreSQL; Redis lưu `user_sequence:{user_id}` (100 events) phục vụ BiLSTM context và `RecommendationPipeline`.

### 3.2.3 Hai luồng gợi ý song song (quan trọng)

| Tiêu chí | Luồng A — Production UI | Luồng B — MLOps API |
|----------|-------------------------|---------------------|
| Entry | `GET /recommendations/<customer_id>/` | `GET /api/v1/recommendations/personal` |
| Class | `RecommenderService` | `RecommendationPipeline` |
| Candidate | Matrix CF + co-occurrence + orders | Neo4j graph walk |
| Ranking | Weighted sum 6 tầng + BiLSTM bias | `model-serving-service` POST `/predict` |
| Cache | `RecommendationLog` | `InferenceCache` (TTL 5 phút) |
| Trạng thái | **Đầy đủ, đang dùng** | model-serving **mock** |

**Giải thích lý do thiết kế hai luồng:** Luồng A tối ưu cho độ trễ thấp và không phụ thuộc GPU — toàn bộ scoring chạy trong Django process. Luồng B chuẩn bị cho A/B testing (`ModelVersion`), drift detection (`model_drift_worker`) và tách inference ra service riêng — kiến trúc hướng tới production ML nhưng `model-serving-service/app/main.py` hiện chỉ trả score giả `0.99 - i*0.01`.

### 3.2.4 Luồng dữ liệu tổng quát (Data Flow)

```mermaid
sequenceDiagram
    participant UI as Browser / Widget
    participant GW as api-gateway
    participant AI as recommender-ai-service
    participant PS as product-service
    participant GQ as Groq LLM
    participant DB as recommender_db
    participant N4 as Neo4j

    Note over UI,N4: Luồng 1 — Ghi nhận hành vi
    UI->>GW: click / view (behavior_tracking)
    GW->>AI: POST /api/recommender/events/
    AI->>DB: INSERT BehaviorEvent
    AI->>N4: MERGE User-Product edge

    Note over UI,GQ: Luồng 2 — Chat tư vấn
    UI->>GW: POST /ai/chat/
    GW->>AI: POST /api/recommender/chat-ktmp
    AI->>PS: GET /products/ (search / hydrate)
    AI->>AI: hybrid_search + RecommenderService
    AI->>GQ: chat/completions (prompt + context)
    GQ-->>AI: answer text
    AI-->>GW: {answer, products, intent}
    GW-->>UI: JSON response

    Note over UI,DB: Luồng 3 — Gợi ý trang chủ
    UI->>GW: GET /recommendations/{id}/
    GW->>AI: proxy recommendation
    AI->>DB: load BehaviorEvent sequence
    AI->>AI: BiLSTM predict + hybrid score
    AI-->>UI: product_ids + scores
```

### 3.2.5 Bảng thành phần — vai trò và lý do lựa chọn

| Thành phần | Công nghệ (trong repo) | Vai trò | Lý do lựa chọn |
|------------|------------------------|---------|----------------|
| Web framework | Django 4 + DRF | REST API, ORM, management commands | Đồng bộ stack với các service khác |
| LLM inference | Groq (llama-3.1-8b-instant) | Sinh câu trả lời tiếng Việt | Miễn phí tier, latency thấp, API OpenAI-compatible |
| Embedding | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 | Dense retrieval đa ngôn ngữ | Hỗ trợ tiếng Việt, chạy CPU được |
| Sparse retrieval | sklearn TfidfVectorizer | Bắt keyword chính xác (SKU, tên) | Nhẹ, không cần GPU |
| Graph DB | Neo4j 5 Community | Lưu quan hệ user–product realtime | Cypher expressive cho CF trên đồ thị |
| Graph offline | NetworkX + pickle | RAG fallback cho dataset U00x | Không cần Neo4j khi dev offline |
| Sequence model | TensorFlow Keras BiLSTM | Dự đoán next action | Artifact đạt 77.3% accuracy |
| Matrix CF | sklearn NMF | Collaborative filtering | Train offline, load nhanh từ npz |
| Message queue | RabbitMQ | Đồng bộ catalog/user/interaction events | Đã có trong docker-compose hệ thống |
| Cache | Redis 7 | User sequence + trending | In-memory, TTL theo giờ |

### Nhận xét mục 3.2

Kiến trúc AI-Service của đồ án là **kiến trúc lai (hybrid)**: kết hợp symbolic graph, statistical CF, neural sequence model và generative LLM. Không có một "model duy nhất" giải quyết tất cả — mỗi tầng xử lý một phần bài toán, ghép tại `RAGChatLLM.chat()` và `RecommenderService.recommend()`."""

SEC_33 = r"""## 3.3 KNOWLEDGE BASE

### 3.3.1 Knowledge Base là gì?

Trong ngữ cảnh đồ án, **Knowledge Base (KB)** là tập tri thức có cấu trúc và bán cấu trúc mà AI-Service sử dụng để **không bịa đặt** thông tin sản phẩm khi trả lời khách hàng. KB không phải một database duy nhất mà là **tổ hợp nhiều nguồn** được chuẩn hóa qua pipeline:

| Lớp KB | Nguồn gốc | Định dạng lưu trữ | File / Model liên quan |
|--------|-----------|-------------------|------------------------|
| Catalog KB | `product-service` REST API | Text document + pickle index | `catalog_hybrid_index.pkl` |
| Behavior KB | `BehaviorEvent`, RabbitMQ events | PostgreSQL rows | `app/models/behavior_event.py` |
| Graph KB (offline) | `data_user500.csv` | NetworkX graph pickle | `rag/rag_system.pkl` |
| Graph KB (online) | Interaction/Payment events | Neo4j nodes/edges | `event_handler.py` |
| Projection KB | Catalog/User events | `ProductProjection`, `UserProjection` | `app/models/projection.py` |
| Policy KB | Hardcoded trong code | Python string | `RAGChatLLM._policy_context()` |

**Không tìm thấy trong source code dự án:** thư mục `app/services/ai_engine/kb/` được mount trong `docker-compose.yml` nhưng **không chứa file dữ liệu** — KB thực tế nằm ở `rag/` và `data/`.

### 3.3.2 Vai trò Knowledge Base trong hệ thống

1. **Cho RAG:** Cung cấp `suggested_products` trong prompt LLM — LLM chỉ diễn đạt lại, không tự nghĩ ra giá/tồn kho.
2. **Cho Hybrid Search:** Mỗi sản phẩm được chuyển thành document text qua `_product_doc()` — ghép name, description, SKU, category, brand, attributes.
3. **Cho Recommendation:** `ProductCatalog.get_products()` cache metadata phục vụ category affinity và lọc sản phẩm active.
4. **Cho GraphRAG:** CSV và Neo4j cung cấp quan hệ user–product để mở rộng ngữ cảnh "khách tương tự đã mua gì".

### 3.3.3 Nguồn dữ liệu chi tiết

| Nguồn | Service gốc | Trường dữ liệu chính | Cách AI-Service tiếp cận |
|-------|-------------|----------------------|--------------------------|
| **Product** | product-service | id, name, description, price, effective_price, stock, category, brand, sku, attributes | `HybridProductRetriever._fetch_all_products()`, `ProductCatalog` |
| **Category** | product-service (nested) | category_id, category.name | Đưa vào document text và `category_affinity` |
| **Brand** | product-service (nested) | brand.name | Đưa vào TF-IDF document |
| **Review** | interaction-service | event_type=REVIEW | **Một phần:** `BehaviorEvent` nếu được sync; không có pipeline review text riêng cho RAG |
| **Order** | order-service | order items, customer_id | `GET /orders/internal/recommender-orders/` cho co-purchase |
| **FAQ / Policy** | Không có DB riêng | Đổi trả, giao hàng | Hardcode `_policy_context()` khi `intent=POLICY` |
| **User Behavior** | interaction + payment + UI tracking | view, click, add_to_cart, purchase | `BehaviorEvent`, `POST /api/recommender/events/`, RabbitMQ consumer |

**Review dạng văn bản cho embedding:** Không tìm thấy pipeline import review text vào `catalog_hybrid_index.pkl`. Review chỉ xuất hiện như **loại hành động** trong BiLSTM (`action=review`).

### 3.3.4 Pipeline xây dựng Knowledge Base

```mermaid
flowchart LR
    subgraph COLLECT["1. Data Collection"]
        C1[product-service GET /products/]
        C2[interaction RabbitMQ]
        C3[payment.succeeded events]
        C4[UI behavior_tracking POST events]
        C5[data_user500.csv — seed]
    end

    subgraph CLEAN["2. Data Cleaning"]
        CL1[Lọc is_active products]
        CL2[normalize_action]
        CL3[Chặn PURCHASE giả từ interaction stream]
        CL4[Tokenize tiếng Việt _tokenize_vi]
    end

    subgraph TRANSFORM["3. Data Transformation"]
        T1[_product_doc — ghép text field]
        T2[LabelEncoder — BiLSTM features]
        T3[MERGE Cypher — Neo4j]
        T4[NetworkX MultiDiGraph build]
    end

    subgraph ENRICH["4. Data Enrichment"]
        E1[Fetch price_tier từ product metadata]
        E2[goal inference từ action]
        E3[Co-purchase từ order-service]
        E4[Category affinity aggregation]
    end

    subgraph STORE["5. Data Storage"]
        S1[(recommender_db — BehaviorEvent)]
        S2[catalog_hybrid_index.pkl]
        S3[rag_system.pkl]
        S4[(Neo4j graph)]
        S5[(Redis sequences)]
    end

    C1 --> CL1 --> T1 --> S2
    C2 --> CL2 --> T2 --> S1
    C3 --> CL3 --> E1 --> S1
    C4 --> CL2 --> S1
    C5 --> T4 --> S3
    S1 --> E4 --> S4
    S1 --> E2 --> S5
```

#### Bước 1 — Data Collection (Thu thập)

**Catalog:** Command `build_catalog_index` (`app/management/commands/build_catalog_index.py`) gọi `get_hybrid_retriever().rebuild_index()`. Hàm `_fetch_all_products()` paginate `page_size=200`, tối đa 10 trang — lấy toàn bộ sản phẩm active từ `product-service`.

**Behavior realtime:** `api-gateway/gateway/behavior_tracking.py` gửi sự kiện tới recommender. `consume_events` command subscribe RabbitMQ routing keys: `catalog.product.*`, `interaction.*`, `payment.succeeded`, `user.*`.

**Seed offline:** File `data/data_user500.csv` (~41.000 dòng, 500 users) dùng khởi tạo NetworkX graph và script `rebuild_neo4j.cypher`.

#### Bước 2 — Data Cleaning (Làm sạch)

- **Sản phẩm:** Chỉ index sản phẩm có `id` hợp lệ; bỏ inactive khi hydrate recommendation.
- **Hành vi:** `EventHandler.handle_interaction_event()` **từ chối** event `PURCHASE` từ interaction stream thô — purchase chỉ đến từ `payment.succeeded` để tránh dữ liệu giả.
- **Text:** `_tokenize_vi()` loại ký tự đặc biệt, giữ dấu tiếng Việt cho TF-IDF.

#### Bước 3 — Data Transformation (Biến đổi)

Mỗi sản phẩm → document:

```python
# rag/hybrid_retriever.py — _product_doc()
parts = [name, description, sku, category_name, brand_name, attributes]
return _tokenize_vi(" ".join(parts))
```

Mỗi hành vi → sequence feature 18 chiều (cho BiLSTM) qua `BehaviorPredictionService._build_sequence_frame()`.

#### Bước 4 — Data Enrichment (Làm giàu)

- **Giá:** `_price_tier()` chia low/mid/high theo ngưỡng 100k/300k VND.
- **Goal:** `_goal_from_action()` suy ra browsing/buying/comparing/...
- **Order:** `_fetch_recommender_orders()` lấy lịch sử mua cho co-purchase scoring.

#### Bước 5 — Data Storage (Lưu trữ)

| Artifact | Kích thước điển hình | Tái tạo |
|----------|---------------------|---------|
| `catalog_hybrid_index.pkl` | ~vài MB (phụ thuộc catalog) | `build_catalog_index --force` |
| `rag_system.pkl` | Serialize NetworkX + RAGSystem | Tự build từ CSV khi thiếu |
| `data/implicit_cf/*.npz` | Ma trận NMF | `train_implicit_cf_local` |
| Neo4j | Persistent volume `neo4j_data` | `rebuild_neo4j.cypher` hoặc realtime MERGE |

### 3.3.5 Giải thích Pipeline cho người đọc chưa biết AI

Hãy tưởng tượng KB như **thư viện của nhân viên tư vấn**:
- Kệ **Catalog** chứa hồ sơ từng sản phẩm (tên, mô tả, giá).
- Sổ **Behavior** ghi chép ai đã xem/mua gì.
- Bảng **Graph** ghim mối quan hệ "khách A và khách B cùng thích sản phẩm X".
- Chatbot **không được phép** trả lời nếu không mở ít nhất một trong các nguồn trên — đó là nguyên tắc RAG (mục 3.5).

### Nhận xét mục 3.3

Knowledge Base của đồ án **không dùng CMS hay Elasticsearch** mà xây trực tiếp từ API microservice và sự kiện — phù hợp kiến trúc event-driven đã có. Điểm cần mở rộng: tích hợp review text và FAQ động từ database."""

SEC_34 = r"""## 3.4 VECTOR DATABASE

### 3.4.1 Phân tích các công nghệ Vector DB phổ biến

| Công nghệ | Có trong dự án? | Ghi chú |
|-----------|-----------------|---------|
| **ChromaDB** | **Không** | Không có import, config hay container |
| **FAISS** | **Dependency only** | `faiss-cpu>=1.7.4` trong `requirements.txt` nhưng **không có `import faiss`** trong toàn repo |
| **Milvus** | **Không** | — |
| **Pinecone** | **Không** | — |
| **In-memory numpy + pickle** | **Có — đang dùng** | `catalog_hybrid_index.pkl` |

**Kết luận mục 3.4:** Đồ án **không triển khai Vector Database riêng** mà dùng **vector embedding trong bộ nhớ** kết hợp **pickle persistence**, đủ cho quy mô catalog hiện tại (hàng trăm SKU).

### 3.4.2 Embedding — khái niệm và cách triển khai

**Embedding** là cách biến text thành vector số (ví dụ 384 chiều) sao cho hai câu gần nghĩa có vector gần nhau. Trong `hybrid_retriever.py`:

```python
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
texts = [f"passage: {d}" for d in self.docs]
self._embeddings = self._encoder.encode(texts, normalize_embeddings=True)
```

**Giải thích dễ hiểu:** Mỗi sản phẩm được "đóng gói" thành một dãy số. Câu hỏi khách cũng được đóng gói tương tự. Hệ thống tìm các dãy số sản phẩm **gần nhất** với dãy số câu hỏi.

**Fallback khi transformer lỗi:** `TruncatedSVD` trên ma trận TF-IDF, 96 chiều — đảm bảo chatbot vẫn chạy trên máy không tải được sentence-transformers.

### 3.4.3 Vector Search và Similarity Search

Sau khi có embedding query và embedding sản phẩm, hệ thống tính **cosine similarity**:

```python
# sklearn.metrics.pairwise.cosine_similarity
sim = cosine_similarity(query_vec, self._embeddings).ravel()
```

**Top-K Retrieval:** Biến môi trường `CHAT_TOP_K=5` (mặc định) — chỉ lấy 5 sản phẩm khớp nhất sau fusion và rerank.

### 3.4.4 Cấu trúc dữ liệu `catalog_hybrid_index.pkl`

| Key trong pickle | Kiểu | Mô tả |
|------------------|------|-------|
| `catalog` | list[dict] | Raw product JSON từ product-service |
| `docs` | list[str] | Document text đã tokenize |
| `product_ids` | list[int] | ID tương ứng từng doc |
| `tfidf` | TfidfVectorizer | Vectorizer đã fit (8000 features, ngram 1-2) |
| `tfidf_matrix` | sparse matrix | Ma trận TF-IDF toàn catalog |
| `embeddings` | ndarray | Dense vectors (N × D) |
| `embedding_mode` | str | `transformer` / `svd` / `none` |
| `built_at` | float | Unix timestamp lần build |

### 3.4.5 Quy trình truy xuất (Retrieval Flow)

```mermaid
flowchart TD
    Q[User Query] --> SP[Sparse — TF-IDF cosine]
    Q --> DE[Dense — Sentence Transformer]
    SP --> RRF[Reciprocal Rank Fusion k=60]
    DE --> RRF
    RRF --> CE[Cross-Encoder Rerank top-20]
    CE --> TOP[Top-K=5 products]
```

**RRF (Reciprocal Rank Fusion):** Kết hợp xếp hạng sparse và dense mà không cần chuẩn hóa score trực tiếp — công thức `score += 1/(k + rank)` với `HYBRID_RRF_K=60`.

**Rerank:** `ProductReranker` dùng `cross-encoder/mmarco-mMiniLMv2-L384-v1` hoặc feature-based fallback (`product_reranker.py`).

### 3.4.6 So sánh thiết kế hiện tại vs Vector DB chuyên dụng

| Tiêu chí | Pickle + in-memory (hiện tại) | ChromaDB/Milvus (không có) |
|----------|-------------------------------|----------------------------|
| Quy mô catalog | < 10k SKU — phù hợp | > 100k SKU |
| Latency | Thấp (RAM) | Cần network hop |
| Incremental update | Phải rebuild index | Hỗ trợ insert từng vector |
| Ops complexity | Thấp — không thêm container | Cao — cluster, shard |

### Nhận xét mục 3.4

Vector search trong đồ án **thực chất là hybrid retrieval** chứ không phải vector DB độc lập. Đây là lựa chọn hợp lý cho đồ án tốt nghiệp quy mô vừa; khi catalog lên hàng triệu SKU cần cân nhắc FAISS (đã có dependency) hoặc Milvus."""

SEC_35 = r"""## 3.5 RAG (RETRIEVAL AUGMENTED GENERATION)

### 3.5.1 RAG là gì?

**Retrieval Augmented Generation (RAG)** là mô hình kết hợp hai bước:
1. **Retrieval (Truy xuất):** Tìm thông tin liên quan từ kho tri thức (catalog, graph, behavior).
2. **Generation (Sinh văn bản):** Đưa thông tin đã truy xuất vào prompt, nhờ LLM viết câu trả lời tự nhiên.

Trong đồ án, lớp trung tâm là `RAGChatLLM` (`rag/rag_llm.py`), endpoint `KTMPChatConsultingView` (`app/views/rag_views.py`).

### 3.5.2 Tại sao cần RAG?

| Vấn đề LLM thuần | Hậu quả trong E-Commerce | RAG giải quyết |
|------------------|--------------------------|----------------|
| Không biết giá/tồn kho hôm nay | Báo sai giá → mất niềm tin | Inject `suggested_products` từ product-service |
| Hallucination tên sản phẩm | Gợi ý SKU không tồn tại | Chỉ liệt kê product_id có trong retrieval |
| Không biết lịch sử user | Tư vấn chung chung | Ghép `recent_behaviors`, `next_action_prediction` |
| Kiến thức cắt tại training cutoff | Không biết catalog mới | Rebuild index từ API live |

### 3.5.3 Hạn chế của LLM nếu không dùng RAG (trong bối cảnh đồ án)

Nếu chỉ gọi `call_groq()` với system prompt mà **không** có `context_text`, model `llama-3.1-8b-instant` sẽ:
- Tự nghĩ ra sản phẩm ("iPhone 15 giảm 50%") không có trong `product-service`.
- Không tạo link `/products/{id}/` đúng format mà `_postprocess_answer()` yêu cầu.
- Không phân biệt intent mua hàng vs hỏi chính sách.

Code thực tế **luôn** xây `context_text` trước khi gọi Groq:

```python
context_text = (
    f"intent: {intent.value}\n"
    f"customer_id: {user_id}\n"
    f"suggested_products:\n{product_block}\n"
    f"next_action_prediction: {next_action_prediction}"
)
```

### 3.5.4 Quy trình hoạt động RAG trong hệ thống

```mermaid
sequenceDiagram
    participant U as User
    participant LLM as RAGChatLLM
    participant IR as IntentRouter
    participant HR as HybridRetriever
    participant RS as RecommenderService
    participant GQ as Groq API

    U->>LLM: message + history + recent_behaviors
    LLM->>IR: classify_intent(message, history)
    IR-->>LLM: SEARCH / RECOMMEND / POLICY / ...
    LLM->>HR: hybrid_search(retrieval_query)
    HR-->>LLM: top-K products (sparse+dense+RRF)
    alt customer_id là integer (user thật)
        LLM->>RS: recommend_with_prediction(customer_id)
        RS-->>LLM: rec_ids + next_action_prediction
    else user dataset U001
        LLM->>LLM: RAGSystem.recommend_products()
    end
    LLM->>LLM: build context_text + system prompt Mochi
    LLM->>GQ: POST chat/completions
    GQ-->>LLM: answer markdown
    LLM->>LLM: _postprocess_answer (fix links)
    LLM-->>U: {answer, products, intent}
```

### 3.5.5 Giải thích từng bước pipeline RAG

| Bước | Tên kỹ thuật | Implementation | Input → Output |
|------|--------------|----------------|----------------|
| 1 | **Query** | `message` từ user | "Tìm son môi màu đỏ" |
| 2 | **Intent Classification** | `classify_intent()` | → `ChatIntent.SEARCH` |
| 3 | **Retrieval Query Build** | `build_retrieval_query()` | Ghép message + keyword từ history |
| 4 | **Embedding** | SentenceTransformer encode query | text → vector 384d |
| 5 | **Vector Search** | cosine similarity + TF-IDF | → ranked product list |
| 6 | **Context Retrieval** | `_format_products_for_prompt()` | → text block giá/tên/stock |
| 7 | **Prompt Construction** | system prompt Mochi + context | → messages[] |
| 8 | **LLM Generation** | `call_groq()` | → answer tiếng Việt |
| 9 | **Post-process** | `_postprocess_answer()` | Chuẩn hóa link `/products/{id}/` |

### 3.5.6 Sơ đồ kiến trúc RAG

```mermaid
flowchart TB
    subgraph Input
        MSG[User Message]
        HIST[History ≤10 turns]
        BEH[recent_behaviors]
    end

    subgraph RetrievalLayer["Retrieval Layer"]
        INT[intent_router.py]
        HYB[hybrid_retriever.py]
        KW[_search_catalog — product-service]
        REC[RecommenderService / RAGSystem]
    end

    subgraph GenerationLayer["Generation Layer"]
        CTX[Context Builder]
        GROQ[Groq llama-3.1-8b-instant]
        POST[Post-process links]
    end

    MSG --> INT
    HIST --> INT
    INT --> HYB
    INT --> REC
    HYB --> CTX
    KW --> CTX
    REC --> CTX
    BEH --> CTX
    CTX --> GROQ --> POST
```

### 3.5.7 Ưu điểm và nhược điểm RAG trong đồ án

**Ưu điểm:**
- Câu trả lời bám catalog thật — kiểm chứng được qua `product_id`.
- Tách biệt retrieval và generation — đổi LLM provider không cần retrain embedding.
- Hỗ trợ tiếng Việt qua model multilingual embedding + prompt tiếng Việt.

**Nhược điểm:**
- Phụ thuộc chất lượng index: nếu `build_catalog_index` fail, retrieval rỗng.
- Latency = retrieval + Groq (timeout 20s) — có thể chậm trên máy yếu.
- Không có reranker LLM (self-RAG) — chỉ một vòng retrieval.

### 3.5.8 Trường hợp sử dụng cụ thể

| Intent | Hành vi hệ thống | Ví dụ |
|--------|------------------|-------|
| `SEARCH` | Ưu tiên `hybrid_search` + lọc giá | "son dưới 200k" |
| `RECOMMEND` | Ưu tiên `RecommenderService` | "gợi ý quà tặng" |
| `POLICY` | `_policy_context()` hardcoded | "đổi trả trong bao lâu?" |
| `GREETING` | Prompt chào hỏi Mochi | "xin chào" |

### Nhận xét mục 3.5

RAG trong đồ án là **production path thực sự** — không phải demo. Mọi bước đều có file Python tương ứng, có fallback khi Groq không khả dụng."""

SEC_36 = r"""## 3.6 GRAPH RAG (GRAPHRAG)

### 3.6.1 GraphRAG là gì?

**GraphRAG** mở rộng RAG truyền thống bằng cách dùng **đồ thị tri thức (Knowledge Graph)** để:
- Truy vấn quan hệ đa bước (user → product → category → similar product).
- Kết hợp hành vi lân cận trên graph làm ngữ cảnh cho LLM và recommender.

Trong đồ án, GraphRAG **không phải một thư viện riêng** (không có Microsoft GraphRAG SDK) mà là **sự kết hợp**:
1. `RAGSystem` (NetworkX) — retrieval theo neighbor trên graph CSV.
2. Neo4j — candidate retrieval và realtime sync.
3. `RAGChatLLM` — ghép kết quả graph + vector retrieval vào prompt.

### 3.6.2 Khác gì với RAG truyền thống?

| Tiêu chí | RAG truyền thống (vector only) | GraphRAG (đồ án) |
|----------|-------------------------------|------------------|
| Đơn vị truy xuất | Document text | Node + Edge + Document |
| Quan hệ nhiều bước | Khó ("sản phẩm cùng danh mục với thứ đã mua") | Cypher / NetworkX walk |
| Cá nhân hóa | Chỉ theo query text | Theo subgraph quanh `user_id` |
| Cập nhật | Rebuild index | MERGE edge realtime (Neo4j) |

### 3.6.3 Tại sao hệ thống E-Commerce cần GraphRAG?

E-Commerce có **quan hệ mạng tự nhiên**: khách mua A thường xem B, sản phẩm thuộc category C, brand D. Vector search đơn thuần có thể trả về sản phẩm **ngữ nghĩa giống** nhưng **không liên quan hành vi**. Graph bổ sung tín hiệu **collaborative** — "người giống bạn đã làm gì".

### 3.6.4 Khái niệm đồ thị trong đồ án

| Khái niệm | Định nghĩa | Ví dụ trong repo |
|-----------|------------|------------------|
| **Node (Nút)** | Thực thể | `User`, `Product`, `Category`, `Action` |
| **Relationship (Cạnh)** | Quan hệ có hướng | `PERFORMED`, `BELONGS_TO`, `PURCHASED`, `VIEW` |
| **Knowledge Graph** | Tập node + edge | NetworkX `MultiDiGraph` hoặc Neo4j store |
| **Entity** | Đối tượng có ID | `user_id=42`, `product_id=15` |
| **Ontology** | Tập loại quan hệ cho phép | action types trong `behavior_actions.py` |
| **Semantic Relation** | Quan hệ có ý nghĩa nghiệp vụ | `co-purchase`, `category affinity` |

### 3.6.5 Phân tích các quan hệ trong hệ thống

```mermaid
graph LR
    U[User] -->|PERFORMED / VIEW / PURCHASED| P[Product]
    P -->|BELONGS_TO| C[Category]
    P -->|HAS_BRAND| B[Brand]
    P -->|REVIEWED_BY| U
    P -->|SIMILAR_TO| P2[Product]
    U -->|PLACED| O[Order]
    O -->|CONTAINS| P
```

**Ánh xạ với source code:**

| Quan hệ | Có trong code? | Cách triển khai |
|---------|----------------|-----------------|
| User → Product | **Có** | Neo4j `MERGE (u)-[r:VIEW]->(p)`; CSV `PERFORMED` edge |
| User → Order | **Gián tiếp** | `order-service` API, không có Order node Neo4j trong runtime MERGE |
| Product → Category | **Có** | `BELONGS_TO` trong `rebuild_neo4j.cypher`; metadata trong catalog |
| Product → Brand | **Một phần** | Brand name trong `_product_doc()`, không có Brand node Neo4j runtime |
| Product → Review | **Một phần** | Action `review` trong BiLSTM, không có Review node |
| Product → Similar Product | **Có** | `ImplicitCFEngine`, `get_cooccurrence_scores()` |
| Order → Product | **Có** | Co-purchase scoring từ `recommender-orders` |

### 3.6.6 Sơ đồ Graph chi tiết (NetworkX — RAGSystem)

```mermaid
graph TD
    subgraph Users
        U1[U001]
        U2[U002]
    end
    subgraph Products
        P1[product_id: 101]
        P2[product_id: 205]
        P3[product_id: 310]
    end
    subgraph Categories
        C1[fashion]
        C2[beauty]
    end
    U1 -->|PERFORMED action=purchase| P1
    U1 -->|PERFORMED action=view| P2
    U2 -->|PERFORMED action=purchase| P1
    U2 -->|PERFORMED action=add_to_cart| P3
    P1 -->|BELONGS_TO| C1
    P2 -->|BELONGS_TO| C1
    P3 -->|BELONGS_TO| C2
```

**Giải thích:** `RAGSystem.retrieve_similar_users()` tìm user có Jaccard similarity trên tập sản phẩm đã mua/thêm giỏ — **loại trừ super-node** (sản phẩm quá phổ biến) để tránh bias "ai cũng mua sản phẩm đó".

### 3.6.7 Vai trò GraphRAG trong luồng chat

Khi `customer_id` không parse được integer (user dạng `U001` từ dataset), `RAGChatLLM.chat()` fallback:

```python
v_history = self.rag.retrieve_user_history(user_id, top_k=5)
recs = self.rag.recommend_products(user_id)
```

Đây chính là **GraphRAG retrieval** — context từ đồ thị thay vì chỉ vector catalog.

### Nhận xét mục 3.6

GraphRAG trong đồ án là **kiến trúc thực tế hai tầng graph** (NetworkX offline + Neo4j online), không phải marketing term. Điểm chưa hoàn thiện: chưa merge hai graph thành một nguồn thống nhất."""

SEC_37 = r"""## 3.7 NEO4J KNOWLEDGE GRAPH

### 3.7.1 Neo4j Architecture trong đồ án

Neo4j chạy container `neo4j:5-community` (`docker-compose.yml`):
- **HTTP Browser:** port `7474`
- **Bolt protocol:** port `7687` — Python driver kết nối qua `neo4j_uri = bolt://neo4j:7687`
- **Auth:** `NEO4J_AUTH=neo4j/password123`
- **Persistence:** volume `./neo4j_data:/data`

Driver khởi tạo trong `app/services/event_handler.py`:

```python
from neo4j import GraphDatabase
neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
```

### 3.7.2 Thiết kế Node

| Label | Properties | Nguồn tạo |
|-------|------------|-----------|
| `User` | `id` (runtime) hoặc `user_id` (bulk CSV) | `EventHandler._update_neo4j_graph`, `rebuild_neo4j.cypher` |
| `Product` | `id`, `name`, `category` | MERGE từ events / CSV |
| `Category` | `name` | `rebuild_neo4j.cypher` |
| `Action` | `name` | `rebuild_neo4j.cypher` (bulk only) |

**Lưu ý inconsistency:** Script bulk dùng `user_id`/`product_id`; runtime MERGE dùng `id`. Đây là điểm cần thống nhất khi mở rộng — hiện tại `RecommendationPipeline` query `User {id: $user_id}` khớp runtime path.

### 3.7.3 Thiết kế Relationship

| Relationship | Ý nghĩa | Properties | Tạo bởi |
|--------------|---------|------------|---------|
| `PERFORMED` | Hành vi tổng quát (bulk CSV) | action, timestamp, device | `rebuild_neo4j.cypher` |
| `VIEW` | Xem sản phẩm | weight, last_interaction, interaction_count | `EventHandler` |
| `PURCHASED` | Mua (từ payment) | weight (+10.0) | `EventHandler` |
| `ADDED_TO_CART` | Thêm giỏ | weight | `EventHandler` (map từ ADD_TO_CART) |
| `BELONGS_TO` | Product → Category | — | bulk CSV |

### 3.7.4 Pipeline ETL — xây graph từ database

```mermaid
flowchart LR
    subgraph Extract
        E1[RabbitMQ events]
        E2[data_user500.csv]
        E3[recommender_db BehaviorEvent]
    end
    subgraph Transform
        T1[Map event_type → edge label]
        T2[Aggregate weight]
    end
    subgraph Load
        L1[Neo4j MERGE runtime]
        L2[LOAD CSV bulk cypher]
    end
    E1 --> T1 --> L1
    E2 --> L2
    E3 --> T1
```

**Realtime path:** `recommender-consumer` → `EventHandler._process_interaction()` → `_update_neo4j_graph()`.

**Bulk path:** `rebuild_neo4j.cypher` xóa toàn graph (`DETACH DELETE`) rồi `LOAD CSV` từ `file:///data_user500.csv`.

### 3.7.5 Đồng bộ dữ liệu

| Kênh | Trigger | Đích |
|------|---------|------|
| RabbitMQ `interaction.*` | User view/click/cart | Neo4j + Redis + PostgreSQL |
| RabbitMQ `payment.succeeded` | Thanh toán thành công | Edge PURCHASED weight=10 |
| RabbitMQ `catalog.product.*` | CRUD sản phẩm | `ProductProjection` (PostgreSQL, không tự động tạo Product node Neo4j) |
| Manual | Dev seed | `rebuild_neo4j.cypher` |

### 3.7.6 Ví dụ Cypher Query và giải thích

**Query 1 — Cập nhật tương tác (runtime, từ Python f-string):**

```cypher
MERGE (u:User {id: $user_id})
MERGE (p:Product {id: $product_id})
MERGE (u)-[r:VIEW]->(p)
SET r.weight = coalesce(r.weight, 0) + $weight,
    r.last_interaction = datetime(),
    r.interaction_count = coalesce(r.interaction_count, 0) + 1
```

*Giải thích:* `MERGE` đảm bảo idempotent — gọi nhiều lần không nhân đôi node. `weight` cộng dồn thể hiện mức độ quan tâm. `interaction_count` hỗ trợ debug/analytics.

**Query 2 — Collaborative filtering candidates (`recommendation_pipeline.py`):**

```cypher
MATCH (u:User {id: $user_id})-[:PURCHASED|ADDED_TO_CART]->(p:Product)
      <-[:PURCHASED|ADDED_TO_CART]-(other:User)-[:PURCHASED]->(rec:Product)
WHERE NOT (u)-[:PURCHASED]->(rec)
RETURN rec.id as product_id, count(*) as score
ORDER BY score DESC
LIMIT 100
```

*Giải thích:* Tìm sản phẩm `rec` mà những user `other` (cùng quan tâm sản phẩm `p` với u) đã mua, nhưng u chưa mua. Đây là **item-based CF trên graph** — cốt lõi GraphRAG cho luồng MLOps.

**Query 3 — Bulk load (`rebuild_neo4j.cypher`):**

```cypher
LOAD CSV WITH HEADERS FROM 'file:///data_user500.csv' AS row
MERGE (u:User {user_id: row.user_id})
MERGE (p:Product {product_id: row.product_id})
  ON CREATE SET p.name = row.product_name, p.category = row.category
MERGE (c:Category {name: row.category})
MERGE (p)-[:BELONGS_TO]->(c);
```

*Giải thích:* Nạp toàn bộ dataset vào graph tĩnh phục vụ visualize và thử nghiệm trong Neo4j Browser (`scripts/neo4j_visualize_kg.cypher`, `scripts/neo4j_advanced_queries.cypher`).

### 3.7.7 Neo4j vs NetworkX trong đồ án

| | Neo4j | NetworkX (RAGSystem) |
|---|-------|---------------------|
| Dữ liệu | Events thật từ hệ thống | CSV `data_user500.csv` |
| Query | Cypher | Python API |
| Use case | MLOps candidates, analytics | Chat fallback user U00x |
| Scale | Persistent, indexed | In-memory pickle |

### Nhận xét mục 3.7

Neo4j trong đồ án **đã tích hợp production** qua event handler, không chỉ diagram. Neo4j GDS plugin và đồng bộ catalog node tự động: **Không tìm thấy trong source code dự án**."""

SEC_38 = r"""## 3.8 DEEP LEARNING MODEL

### 3.8.0 Tổng quan bài toán học máy

| Khía cạnh | Mô tả trong đồ án |
|-----------|-------------------|
| **Bài toán** | Phân loại hành động tiếp theo (next-action prediction) |
| **Input** | Chuỗi 20 bước × 18 features hành vi |
| **Output** | 1 trong 8 classes: search, view, click, wishlist, add_to_cart, remove_from_cart, purchase, review |
| **Feature** | One-hot action + category + device + price_tier + hour + dow + product_id + recency + purchase_norm + step_ratio + goal |
| **Label** | `action` tại timestep kế tiếp sau cửa sổ |

**Mục đích business:** Không chỉ để báo cáo accuracy — `RecommenderService._behavior_bias()` dùng prediction để **tăng/giảm** điểm gợi ý.

### 3.8.1 Recommendation Model

#### Collaborative Filtering (CF)

**Matrix Factorization NMF** — `ImplicitCFEngine` (`app/services/implicit_cf_engine.py`):
- Train offline: `train_implicit_cf_local` command, `sklearn.decomposition.NMF`, `n_components=64`
- Artifacts: `data/implicit_cf/factors.npz` (W, H), `interactions.npz`, `meta.json`
- Runtime: `scores = W[user_idx] @ H` → top product IDs
- Weight trong hybrid: `IMPLICIT_CF_ALS_WEIGHT=4.0` (tên env legacy "ALS" nhưng implementation là NMF)

*Giải thích đơn giản:* Ma trận user–item được phân tích thành hai ma trận nhỏ hơn (factors). Nhân factors suy ra "điểm quan tâm" giữa user và sản phẩm chưa tương tác.

#### Content-Based Filtering

**Category Affinity** — `RecommenderRepository.get_category_affinity()`:
- Đếm tần suất tương tác theo `category_id`
- Boost mạnh `PURCHASE_CATEGORY_WEIGHT=8.0` cho category đã mua
- Gợi ý sản phẩm **chưa từng xem** nhưng cùng category ưa thích

#### Hybrid Recommendation

`RecommenderService` **cộng có trọng số** 6 nguồn điểm (xem mục 3.13 chi tiết). Đây là **hybrid** thực sự — không chỉ một thuật toán.

#### User Embedding & Product Embedding

| Loại | Trong đồ án | File |
|------|-------------|------|
| User factor (CF) | Hàng `W[user_idx]` từ NMF | `factors.npz` |
| Product factor (CF) | Cột `H[:, item_idx]` | `factors.npz` |
| User embedding (DL) | Không tách vector riêng — BiLSTM học hidden state nội bộ | `model_best.keras` |
| Product embedding (DL) | **Không tìm thấy** NCF-style product embedding trong production path | — |
| Text embedding | SentenceTransformer trên catalog doc | `hybrid_retriever.py` |

**ORM placeholder:** `UserFeature.embedding_vector`, `ProductFeature.embedding_vector` (JSONField) — **chưa wired** vào retrieval.

### 3.8.2 Deep Learning Architecture

#### Kiến trúc được deploy: BiLSTM + Multi-Head Self-Attention

```mermaid
graph TD
    IN["Input (batch, 20, 18)"] --> LN[LayerNormalization]
    LN --> B1[BiLSTM 256 units]
    B1 --> LN2[LayerNormalization]
    LN2 --> ATT[MultiHeadSelfAttention d_model=512, heads=8]
    ATT --> B2[BiLSTM 128 units]
    B2 --> DO[Dropout 0.30]
    DO --> FC[Dense softmax — 8 classes]
```

**So sánh với các kiến trúc khác (offline experiment — `models/model_best_evaluation.txt`):**

| Model | Accuracy | F1-macro | Deploy? |
|-------|----------|----------|---------|
| GRU | 0.6274 | 0.6018 | Không |
| LSTM | 0.6930 | 0.6826 | Không |
| **BiLSTM + Attention** | **0.7730** | **0.7598** | **Có — model_best.keras** |

**Các kiến trúc KHÔNG deploy:**
- **BERT / Sentence Transformer:** Dùng cho embedding catalog, **không** fine-tune cho next-action.
- **Transformer encoder (SASRec/BERT4Rec):** Không tìm thấy trong source code dự án (chỉ nhắc trong tài liệu cũ v6).
- **GNN (BipartiteGNN):** `gnn_pipeline.py` — **stub**, import `data_sync` thiếu.
- **DNN/MLP standalone:** Không có — được thay bằng BiLSTM.
- **Neural CF (NCF):** Không tìm thấy trong production code.

#### Custom layer — MultiHeadSelfAttention

Định nghĩa trong `inference_utils.py` — bắt buộc khi load model:

```python
self.model = tf.keras.models.load_model(
    model_path,
    custom_objects={"MultiHeadSelfAttention": MultiHeadSelfAttention},
    compile=False,
)
```

*Giải thích:* Attention cho phép mô hình "nhìn" vào các bước quan trọng trong chuỗi 20 hành động (ví dụ bước `add_to_cart` gần nhất) thay vì chỉ lấy hidden state cuối.

### 3.8.3 CODE STRUCTURE

#### Cấu trúc thư mục Deep Learning & Recommendation

```
recommender-ai-service/
├── inference_utils.py          # UserBehaviorPredictor — inference BiLSTM
├── models/
│   ├── model_best.keras        # Artifact đã train
│   ├── encoders.pkl            # LabelEncoders + SEQ_LEN + ACTIONS
│   └── model_best_evaluation.txt
├── app/services/
│   ├── behavior_prediction_service.py  # Load events → predict
│   ├── recommender_service.py          # Hybrid scoring + bias
│   ├── implicit_cf_engine.py           # NMF inference
│   └── cf_training_utils.py            # Save/load NMF artifacts
├── app/management/commands/
│   ├── train_implicit_cf_local.py        # Train NMF từ BehaviorEvent
│   └── ensure_recommender_models.py    # Auto-train CF nếu thiếu
└── data/
    ├── data_user500.csv                # Dataset offline
    └── implicit_cf/                    # Generated at runtime
```

**Không tìm thấy trong source code dự án:** `train_models_v5.py`, `data/generate_data_v4.py` — script train BiLSTM. Artifact có sẵn nhưng pipeline train không commit trong monorepo.

#### Dataset

| File | Records | Mục đích |
|------|---------|----------|
| `data_user500.csv` | ~41.000 events, 500 users | Train offline (external), RAG graph |
| `user_behavior.csv` | ~1.000 events | Dev seed |
| `BehaviorEvent` (DB) | Runtime | Inference sequence cho user thật |

Cột CSV (header thực tế từ file): `user_id, product_id, product_name, category, action, timestamp, session_id, device, persona`.

#### DataLoader — không có PyTorch DataLoader

Dự án dùng **TensorFlow/Keras** — training xảy ra ngoài repo. Inference build numpy array trong `UserBehaviorPredictor._build_sequence()`:

- Đọc tối đa `SEQ_LEN=20` events gần nhất
- Pad/truncate về đúng 20 bước
- Transform qua `LabelEncoder` trong `encoders.pkl`

#### Class BehaviorPredictionService

| Method | Chức năng |
|--------|-----------|
| `_get_predictor()` | Lazy load `UserBehaviorPredictor` singleton |
| `predict_next_action(customer_id)` | Query `BehaviorEvent`, enrich metadata từ product-service, gọi predict |
| `_build_sequence_frame(events)` | DataFrame → numpy (20, 18) |
| `_goal_from_action()` | Suy goal từ action label |

#### Class UserBehaviorPredictor

| Method | Chức năng |
|--------|-----------|
| `__init__` | Load keras model + encoders |
| `predict(sequence)` | Trả `{action, confidence, probabilities}` |
| `_transform_row()` | Encode 1 timestep |

#### Training & Validation (offline — từ evaluation file)

| Thông số | Giá trị |
|----------|---------|
| Train/Val/Test | 70% / 15% / 15% |
| SEQ_LEN | 20 |
| Epochs | 45 |
| Callbacks | EarlyStopping patience=6, WarmupCosineDecay, ReduceLROnPlateau, ModelCheckpoint |
| Label smoothing | ε = 0.10 |
| Gradient clipping | norm = 1.0 |

#### Inference path (production)

```mermaid
sequenceDiagram
    participant API as NextActionPredictionView
    participant BPS as BehaviorPredictionService
    participant DB as BehaviorEvent ORM
    participant PS as product-service
    participant M as model_best.keras

    API->>BPS: predict_next_action(customer_id)
    BPS->>DB: SELECT last 20 events
    BPS->>PS: GET /products/{id}/ metadata
    BPS->>M: predict(sequence)
    M-->>BPS: action + confidence
    BPS-->>API: JSON response
```

### Nhận xét mục 3.8

Deep Learning trong đồ án **có artifact và inference path hoàn chỉnh**, nhưng **training pipeline không nằm trong repo**. Giảng viên đọc chương này cần hiểu: BiLSTM không phải "AI trang trí" mà trực tiếp điều chỉnh hybrid recommender qua `behavior_bias`."""

SEC_39 = r"""## 3.9 DỮ LIỆU THỰC NGHIỆM

### 3.9.0 Mô tả Dataset

#### Dataset chính — `data_user500.csv`

| Thuộc tính | Giá trị |
|------------|---------|
| Đường dẫn | `recommender-ai-service/data/data_user500.csv` |
| Số bản ghi | ~41.000 events (đối chiếu file thực tế; tài liệu training cũ ghi ~1M cho bản synthetic mở rộng) |
| Số users | 500 (`U001`–`U500`) |
| Số actions | 8 loại |
| Categories | beauty, books, fashion, toys, ... |
| Mục đích | Train BiLSTM (ngoài repo), build NetworkX graph, bulk Neo4j |

#### Cấu trúc cột

| Cột | Kiểu | Ý nghĩa |
|-----|------|---------|
| `user_id` | string | ID người dùng |
| `product_id` | int | ID sản phẩm |
| `product_name` | string | Tên hiển thị |
| `category` | string | Danh mục |
| `action` | enum | Loại hành vi |
| `timestamp` | datetime | Thời điểm |
| `session_id` | string | Phiên |
| `device` | enum | mobile/tablet/desktop |
| `persona` | string | Persona synthetic |

#### Dataset phụ

| File | Records | Ghi chú |
|------|---------|---------|
| `user_behavior.csv` | ~1.000 | Mock dev, integer user/product id |
| `sample_ratings.csv` | 9 | Demo goodbooks cho `train_implicit_cf` |
| `BehaviorEvent` (live) | Thay đổi theo runtime | Nguồn train NMF local |

#### Tiền xử lý dữ liệu (tóm tắt pipeline offline từ evaluation file)

1. **LabelEncoder** cho action, category, device, product_id, price_tier, goal.
2. **Feature engineering** 18 chiều/timestep (thêm `purchase_norm`, `step_ratio` ở v5).
3. **Sliding window** `SEQ_LEN=20`.
4. **Oversampling** rare classes ×4 (review, wishlist, remove_from_cart).
5. **Cache** `.npz` trong `seq_cache/` — **Không tìm thấy thư mục seq_cache trong repo hiện tại** (artifact training ngoài workspace).

### 3.9.1 Kết quả thực nghiệm

#### Bảng 1 — So sánh kiến trúc RNN (v5, từ `model_best_evaluation.txt`)

| Model | Accuracy | Precision* | Recall* | F1-macro | F1-weighted | Epochs |
|-------|----------|------------|---------|----------|-------------|--------|
| GRU | 0.6274 | — | — | 0.6018 | 0.6203 | 45 |
| LSTM | 0.6930 | — | — | 0.6826 | 0.6927 | 45 |
| **BiLSTM** | **0.7730** | — | — | **0.7598** | **0.7703** | 45 |

*Precision/Recall tổng hợp không ghi trong file — F1 per-class có chi tiết.*

#### Bảng 2 — F1-score theo từng class (BiLSTM v5)

| Class | F1-score | Nhận xét |
|-------|----------|----------|
| remove_from_cart | 0.899 | Dễ nhận — pattern rõ |
| view | 0.832 | Phổ biến, học tốt |
| review | 0.819 | Ít mẫu nhưng đã oversample |
| wishlist | 0.810 | Tương tự |
| search | 0.730 | Biên giới mờ với view |
| click | (trung bình) | — |
| add_to_cart | (trung bình) | — |
| purchase | (trung bình) | Quan trọng business |

#### Bảng 3 — So sánh mô hình Recommendation (offline / hệ thống)

| Model / Strategy | Metric | Giá trị | Nguồn |
|------------------|--------|---------|-------|
| BiLSTM next-action | Accuracy | 77.30% | model_best_evaluation.txt |
| Hybrid Recommender | CTR online | Cần `RecommendationFeedback` | ModelMetric ORM |
| NMF CF | Coverage | Phụ thuộc user trong matrix | implicit_cf meta.json |
| Random cold-start | Hit Rate | ~baseline | `strategy=random-cold-start` |
| model-serving mock | NDCG | **Không có** — mock score | main.py skeleton |

**Giải thích chỉ số:**

| Chỉ số | Ý nghĩa | Dùng khi |
|--------|---------|----------|
| **Accuracy** | % dự đoán đúng class | Cân bằng class |
| **Precision** | Trong số dự đoán class X, bao nhiêu đúng | Chi phí false positive cao |
| **Recall** | Trong số thật class X, bắt được bao nhiêu | Không bỏ sót purchase |
| **F1** | Harmonic mean P và R | Imbalanced data |
| **NDCG** | Thứ hạng gợi ý có đúng không | Recommendation ranking |
| **MAP** | Mean Average Precision | Top-K có hit sớm không |
| **Hit Rate** | Ít nhất 1 hit trong top-K | Catalog lớn |

**NDCG/MAP online:** Schema `ModelMetric` hỗ trợ `ndcg_at_k`, `map_at_k`, `hit_rate` — cần dữ liệu `RecommendationFeedback` từ production. **Không có file kết quả NDCG cố định trong repo.**

### 3.9.2 Nhận xét kết quả

**Mô hình tốt nhất — BiLSTM + Attention (v5):**
- Accuracy **77.30%**, vượt LSTM **+8.0pp**, vượt GRU **+14.6pp**.
- Lý do: BiLSTM đọc chuỗi hai chiều (quá khứ + tương lai ngữ cảnh ngắn), Attention tập trung bước quan trọng, LayerNorm + Dropout 0.30 giảm overfit so với v4.

**Điểm mạnh:**
- Dự đoán tốt các hành độnh có pattern (remove_from_cart, view).
- Tích hợp production rõ ràng qua `behavior_bias`.
- Train time ghi nhận ~39.602s trong evaluation file (môi trường train cụ thể).

**Điểm yếu:**
- Script train không có trong repo — khó reproduce từ đầu.
- Accuracy 77% vẫn nghĩa là ~23% sai — cần hybrid backup.
- Class `purchase` khó hơn do imbalance dù đã oversample.
- v6 models (NCF, SASRec, …): **Không tìm thấy code** — không đưa vào bảng chính thức.

**Nguyên nhân chênh lệch GRU vs BiLSTM:**
- GRU ít tham số hơn, khó học pattern dài 20 bước.
- BiLSTM có 2× hidden flow, phù hợp session e-commerce nhiều bước.

### Nhận xét mục 3.9

Phần thực nghiệm **trung thực**: có số liệu BiLSTM từ file artifact; metric recommendation ranking online phụ thuộc feedback thực tế chưa đầy đủ trong repo."""

SEC_310 = r"""## 3.10 DEPLOY AI SERVICE

### 3.10.1 Kiến trúc triển khai

```mermaid
flowchart TB
    subgraph DockerCompose["docker-compose.yml"]
        NG[nginx :80]
        GW[api-gateway]
        AI[recommender-ai-service :8011]
        RC[recommender-consumer]
        MS[model-serving-service :8019]
        N4[neo4j :7474/7687]
        RD[redis :6381]
        RDB[(recommender-db)]
        RMQ[rabbitmq]
    end

    NG --> GW
    GW --> AI
    AI --> RDB
    AI --> N4
    AI --> RD
    RC --> RMQ
    RC --> N4
    RC --> MS
    AI --> PS[product-service]
```

### 3.10.2 Docker & Docker Compose

**recommender-ai-service Dockerfile** (`recommender-ai-service/Dockerfile`):
- Base Python image, install `requirements.txt`
- Copy source, mount volumes `data/`, `rag/`, `common/`

**Volumes quan trọng:**
```yaml
- ./recommender-ai-service/data:/app/data
- ./recommender-ai-service/rag:/app/rag
- ./recommender-ai-service/app/services/ai_engine/kb:/app/.../kb
```

**Entrypoint** (`entrypoint.sh`) tự động:
1. `wait-for-db` + migrate
2. `sync_purchase_behaviors` / `sync_interaction_behaviors`
3. `ensure_recommender_models` (train NMF nếu thiếu)
4. `build_catalog_index`
5. `runserver 0.0.0.0:8000`

### 3.10.3 FastAPI vs Django

| Service | Framework | Port | Vai trò |
|---------|-----------|------|---------|
| recommender-ai-service | **Django** + DRF | 8011→8000 | AI chính — RAG, recommend, events |
| model-serving-service | **FastAPI** | 8019→8000 | Inference skeleton |

**Không tìm thấy:** Django chỉ dùng cho recommender; FastAPI chỉ cho model-serving — không có FastAPI AI gateway riêng.

### 3.10.4 Nginx

NGINX edge proxy tới `api-gateway`, không expose trực tiếp `recommender-ai-service` ra ngoài — đúng pattern bảo mật microservice.

### 3.10.5 GPU vs CPU

| Thành phần | Hardware | Ghi chú |
|------------|----------|---------|
| BiLSTM inference | **CPU** | TensorFlow CPU trong container |
| SentenceTransformer | **CPU** | `encode()` batch 32 |
| Groq LLM | **Cloud API** | Không chạy local GPU |
| NMF CF | **CPU** | numpy/scipy |
| Neo4j | **CPU** | Community edition |

**Không tìm thấy** cấu hình `nvidia-docker` hay CUDA trong `docker-compose.yml`.

### 3.10.6 Biến môi trường AI quan trọng

| Biến | Mặc định | Tác dụng |
|------|----------|----------|
| `GROQ_API_KEY` | từ `env` file | LLM |
| `GROQ_MODEL` | llama-3.1-8b-instant | Model selection |
| `NEO4J_URI` | bolt://neo4j:7687 | Graph |
| `REDIS_URL` | redis://redis:6379/0 | Sequence |
| `IMPLICIT_CF_DATA_DIR` | data/implicit_cf | NMF artifacts |
| `MODEL_SERVING_URL` | http://model-serving-service:8000 | MLOps pipeline |
| `EMBEDDING_MODEL` | paraphrase-multilingual-MiniLM-L12-v2 | Dense retrieval |
| `CHAT_TOP_K` | 5 | RAG top products |

### Nhận xét mục 3.10

Triển khai AI-Service **đủ để chạy end-to-end** qua `docker-compose up`. Điểm cần lưu ý: `GROQ_API_KEY` bắt buộc cho chat chất lượng cao; thiếu key vẫn chạy fallback."""

SEC_311 = r"""## 3.11 TÍCH HỢP CHAT + DEEP LEARNING

### 3.11.1 Tổng quan luồng tích hợp

Đây là **điểm khác biệt** của đồ án: Chatbot không chỉ gọi LLM mà **ghép RAG + GraphRAG + BiLSTM + Hybrid Recommender** trong một request.

```mermaid
sequenceDiagram
    participant U as Người dùng
    participant W as chatbot-widget.js
    participant GW as api-gateway /ai/chat/
    participant RAG as RAGChatLLM
    participant HR as HybridRetriever
    participant GR as RAGSystem Graph
    participant RS as RecommenderService
    participant BPS as BehaviorPredictionService
    participant BIL as BiLSTM model
    participant GQ as Groq LLM

    U->>W: Nhập câu hỏi
    W->>GW: POST {message, user_id, history, recent_behaviors}
    GW->>RAG: proxy chat-ktmp

    RAG->>RAG: classify_intent()
    RAG->>HR: hybrid_search(query)
    HR-->>RAG: search_products[]

    alt customer_id hợp lệ (integer)
        RAG->>RS: recommend_with_prediction()
        RS->>BPS: predict_next_action()
        BPS->>BIL: forward pass (20,18)
        BIL-->>BPS: action + confidence
        BPS-->>RS: next_action_prediction
        RS-->>RAG: rec_ids + scores + prediction
    else user U001 dataset
        RAG->>GR: retrieve_user_history + recommend_products
        GR-->>RAG: graph-based recs
    end

    RAG->>RAG: build context_text + Mochi system prompt
    RAG->>GQ: chat/completions
    GQ-->>RAG: natural language answer
    RAG->>RAG: _postprocess_answer (product links)
    RAG-->>GW: {answer, products, intent}
    GW-->>W: JSON
    W-->>U: Hiển thị chat + product cards
```

### 3.11.2 Giải thích từng bước (dành cho giảng viên)

| Bước | Mô tả | File |
|------|-------|------|
| 1 | Người dùng hỏi | UI widget |
| 2 | Chatbot nhận câu hỏi | `KTMPChatConsultingView.post()` |
| 3 | Phân loại intent | `classify_intent()` — rule-based keyword |
| 4 | RAG truy xuất catalog | `hybrid_search()` TF-IDF + embedding |
| 5 | GraphRAG mở rộng ngữ cảnh | `RAGSystem` hoặc Neo4j-informed recs |
| 6 | Recommendation Engine | `RecommenderService.recommend_with_prediction()` |
| 7 | Deep Learning suy luận | BiLSTM → `next_action_prediction` trong prompt |
| 8 | LLM tạo câu trả lời | `call_groq()` với context đầy đủ |
| 9 | Trả kết quả | JSON + markdown links `/products/{id}/` |

### 3.11.3 Cách Deep Learning ảnh hưởng câu trả lời chat

`next_action_prediction` được inject vào prompt:

```
next_action_prediction: {'action': 'purchase', 'confidence': 0.82, ...}
```

LLM (Mochi) được system prompt hướng dẫn:
- Nếu user sắp purchase → giọng điệu chốt đơn, nhấn mạnh sản phẩm trong `suggested_products`.
- Nếu browsing → gợi ý khám phá, không ép mua.

Đồng thời `RecommenderService` đã dùng prediction để **chọn** sản phẩm đưa vào `suggested_products` — LLM chỉ diễn đạt.

### 3.11.4 recent_behaviors từ frontend

`chatbot-widget.js` gửi `recent_behaviors` từ `sessionStorage` (view product events). `RAGChatLLM._boost_viewed_products()` tăng điểm sản phẩm user vừa xem — **cầu nối UI → AI không cần reload trang**.

### Nhận xét mục 3.11

Tích hợp Chat + DL **có thật trong một hàm** `RAGChatLLM.chat()` — không tách service. Đây là thiết kế monolith-in-microservice hợp lý cho latency thấp."""

SEC_312 = r"""## 3.12 TÍCH HỢP AI VÀO HỆ THỐNG E-COMMERCE

### 3.12.1 Giao diện Chat

| Thành phần | File | Mô tả |
|------------|------|-------|
| Widget JS | `api-gateway/static/chatbot-widget.js` | Bubble chat, gọi `/ai/chat/` |
| Widget CSS | `api-gateway/static/chatbot-widget.css` | Style |
| Embed | `api-gateway/templates/base.html` | Load script toàn site |
| Test UI | `recommender-ai-service/static/test_ui.html` | Dev test trực tiếp service |

**Luồng:** Browser → same-origin `/ai/chat/` → `ai_chat_proxy` → `recommender-ai-service:8011/api/recommender/chat-ktmp`.

### 3.12.2 Giao diện sản phẩm

`product_detail.html` — tracking behavior khi xem sản phẩm, feed vào recommender qua `behavior_tracking.py`:

```javascript
// sessionStorage lưu view_product_{id} cho recent_behaviors
```

### 3.12.3 Giao diện gợi ý sản phẩm

| Vị trí UI | API | Backend |
|-----------|-----|---------|
| Trang chủ | `GET /recommendations/{customer_id}/` (proxy) | `RecommendationView` → `RecommenderService` |
| Home JS | `home-storefront.js` | Fetch recommendations render carousel |

Response mẫu:
```json
{
  "customer_id": 42,
  "recommended_product_ids": [15, 23, 8],
  "recommendation_scores": [{"product_id": 15, "score": 12.45}],
  "next_action_prediction": {"action": "add_to_cart", "confidence": 0.71},
  "strategy": "hybrid+cf+cooccurrence+category"
}
```

### 3.12.4 Giao diện tìm kiếm AI

**Tìm kiếm truyền thống:** product list filter qua `product-service`.

**Tìm kiếm AI:** Thông qua **chatbot** — user gõ "tìm laptop gaming dưới 20 triệu" → `HybridProductRetriever` + LLM trả lời có link sản phẩm.

**Không tìm thấy:** Trang search riêng `/ai-search/` — AI search chỉ qua chat widget.

### 3.12.5 Admin MLOps UI

`api-gateway/gateway/admin_views.py` — `/admin/recommendation/`:
- Xem model versions
- Trigger retrain NMF (`train_implicit_cf_local`)
- Đọc evaluation file BiLSTM

### 3.12.6 Luồng behavior end-to-end

```mermaid
flowchart LR
    A[User clicks product] --> B[behavior_tracking POST event]
    B --> C[BehaviorEvent DB]
    C --> D[BiLSTM sequence]
    C --> E[NMF matrix update offline]
    C --> F[Neo4j edge]
    D --> G[Next visit: better recommendations]
    F --> H[MLOps candidates]
```

### Nhận xét mục 3.12

AI được nhúng vào **3 điểm chạm**: chat widget, homepage recommendations, implicit tracking trên product detail — đủ demo cho đồ án tốt nghiệp."""

SEC_313 = r"""## 3.13 AI RECOMMENDER SYSTEM

> **Đây là phần dài nhất Chương 3** — mô tả toàn bộ pipeline từ hành vi người dùng đến danh sách Top-N sản phẩm, bám sát `RecommenderService` và các thành phần liên quan.

### 3.13.1 Tổng quan Recommendation Pipeline

```mermaid
flowchart TB
    subgraph Input["User Behavior"]
        BE[BehaviorEvent PostgreSQL]
        OR[Order history — order-service]
        PR[BiLSTM next-action prediction]
    end

    subgraph CandidateGen["Candidate Generation"]
        CF[NMF Matrix CF — top 5×limit]
        COO[Co-occurrence similar users]
        COP[Co-purchase same orders]
        CAT[Category affinity unseen products]
        POP[Global + Item popularity]
    end

    subgraph Retrieval["Retrieval & Scoring"]
        WS[Weighted Sum score_map]
        BB[behavior_bias from BiLSTM]
        EX[Exclude purchased items]
    end

    subgraph Ranking["Ranking"]
        SORT[Sort by score descending]
        LIM[Top limit default 10]
    end

    subgraph Rerank["Re-ranking (implicit)"]
        BR[Browsed-not-bought penalty ×0.45]
        PC[Purchase category boost]
    end

    subgraph Output["Top-N Products"]
        OUT[recommended_product_ids + strategy string]
    end

    BE --> CF
    BE --> COO
    OR --> COP
    BE --> CAT
    PR --> BB
    CF --> WS
    COO --> WS
    COP --> WS
    CAT --> WS
    POP --> WS
    BB --> WS
    WS --> EX --> BR --> SORT --> LIM --> OUT
```

### 3.13.2 Thu thập User Behavior

#### Nguồn behavior

| Nguồn | Action types | Weight mặc định |
|-------|--------------|-----------------|
| UI tracking | view, click, search | 1.0 |
| interaction-service | VIEW, CLICK, ADD_TO_CART | từ event payload |
| payment.succeeded | PURCHASE | 10.0 |
| order sync commands | purchase history | `sync_purchase_behaviors` |

#### Lưu trữ — `BehaviorEvent` model

ORM `app/models/behavior_event.py` — các trường chính: `customer_id`, `product_id`, `action`, `timestamp`, `session_id`, `metadata`.

#### Repository — `RecommenderRepository`

| Method | Chức năng |
|--------|-----------|
| `has_behavior_history(customer_id)` | Kiểm tra cold start |
| `get_interacted_product_ids()` | Tập sản phẩm đã chạm |
| `get_behavior_scores()` | Điểm weighted theo action |
| `get_category_affinity()` | Điểm theo category_id |
| `get_cooccurrence_scores()` | Item-item từ user tương tự |
| `get_global_popularity_scores()` | Popular toàn site |
| `save_log()` | Ghi `RecommendationLog` |

### 3.13.3 Embedding trong pipeline

| Tầng | Loại embedding | Vai trò |
|------|----------------|---------|
| Text catalog | SentenceTransformer | Chỉ trong chat search, không trong `RecommenderService` |
| CF latent | NMF W, H | Candidate generation |
| Sequence | BiLSTM internal state | behavior_bias only |

**Lưu ý:** `RecommenderService` **không** gọi SentenceTransformer — embedding text là nhánh chat (`HybridProductRetriever`), tách biệt nhưng bổ sung trong trải nghiệm tổng thể.

### 3.13.4 GraphRAG trong Recommendation

Neo4j **không** nằm trong `RecommenderService.recommend()` trực tiếp. Graph ảnh hưởng qua:
1. **Luồng MLOps** `RecommendationPipeline._retrieve_candidates_neo4j()` — song song.
2. **RAGSystem** khi fallback user dataset trong chat.
3. **Co-occurrence** trong PostgreSQL mirror logic tương tự graph walk.

### 3.13.5 Candidate Generation — chi tiết từng tầng

#### Tầng 1 — Matrix CF (NMF)

```python
# recommender_service.py
cf_limit = max(limit * 5, 20)  # lấy nhiều candidate hơn output
self._blend_matrix_cf(customer_id, score_map, ..., cf_limit, behavior_bias)
```

- `ImplicitCFEngine.recommend()` trả list `(product_id, score)`.
- Nhân `IMPLICIT_CF_ALS_WEIGHT=4.0` × `behavior_bias`.
- Loại sản phẩm đã mua (`exclude | purchased`).

#### Tầng 2 — Co-occurrence

Users có hành vi tương tự → sản phẩm họ thích:
- `seed_products` = top 8 behavior scores ∪ purchased.
- `get_cooccurrence_scores(customer_id, seed_products)`.
- Weight `COOCCURRENCE_WEIGHT=3.0` × behavior_bias.

*Ví dụ:* User A và B cùng xem sản phẩm 10, B mua sản phẩm 25 → gợi ý 25 cho A.

#### Tầng 3 — Co-purchase

Từ `order-service` API `/orders/internal/recommender-orders/`:
- "Người mua X cũng mua Y" — market basket.
- Weight `COPURCHASE_WEIGHT=2.5`.

#### Tầng 4 — Category Affinity

- Content-based: sản phẩm **chưa tương tác** trong category user thích.
- `PURCHASE_CATEGORY_WEIGHT=8.0` boost mạnh category đã mua.
- Weight `CATEGORY_AFFINITY_WEIGHT=2.0` × behavior_bias.

#### Tầng 5 — Global Popularity

- Baseline cho user ít data.
- `GLOBAL_POPULARITY_WEIGHT=1.5`.

#### Tầng 6 — Item CF Popularity

- `_get_item_cf_popularity()` — signal từ factor matrix cột sản phẩm.
- `ITEM_CF_POPULARITY_WEIGHT=1.0`.

### 3.13.6 Deep Learning — behavior_bias

```python
def _behavior_bias(self, prediction_action, prediction_confidence):
    bias = 1.0
    if prediction_action in ("purchase", "add_to_cart"):
        bias += min(0.25, prediction_confidence * 0.25)
    elif prediction_action in ("view", "click", "search"):
        bias -= min(0.10, prediction_confidence * 0.10)
    return max(0.75, bias)
```

**Giải thích:** Khi BiLSTM dự đoán user sắp mua (confidence 0.82), `bias ≈ 1.205` — mọi điểm CF/co-occurrence được khuếch đại, danh sách Top-N thiên về chuyển đổi. Khi user chỉ browsing, bias giảm → gợi ý exploratory hơn.

### 3.13.7 Ranking & Re-ranking

#### Ranking chính

```python
ranked = sorted(score_map.items(), key=lambda x: x[1], reverse=True)
recommended = [pid for pid, _ in ranked[:limit]]
```

#### Re-ranking heuristic

| Rule | Hệ số | Mục đích |
|------|-------|----------|
| Browsed-not-bought trong category chưa mua | ×0.45 | Giảm spam sản phẩm đã xem nhiều |
| Đã purchased | exclude | Không gợi ý lại đã mua |
| Cold start | random shuffle | Diversity |

#### ProductReranker (nhánh chat)

Cross-encoder rerank **chỉ** trong `HybridProductRetriever` — không trong `RecommenderService`. Đây là ranh giới giữa **homepage recommend** vs **chat search**.

### 3.13.8 Personalization

| Trạng thái user | Strategy string | Hành vi |
|-----------------|-----------------|---------|
| Không có history | `random-cold-start` | Xáo trộn catalog |
| Có history | `hybrid+cf+cooccurrence+...` | Weighted hybrid |
| Catalog rỗng | `empty-catalog` | Trả rỗng |

**Personalization depth:** ID customer → toàn bộ pipeline; không có segment marketing — personalization **100% individual** qua behavior matrix.

### 3.13.9 Luồng MLOps song song (`RecommendationPipeline`)

Dành cho API `GET /api/v1/recommendations/personal`:

```mermaid
flowchart LR
    U[user_id] --> AB[A/B ModelVersion bucket]
    AB --> CACHE{InferenceCache hit?}
    CACHE -->|yes| HYDRATE
    CACHE -->|no| N4J[Neo4j CF candidates 100]
    N4J --> REDIS[Redis sequence 100]
    REDIS --> MS[model-serving /predict]
    MS --> CACHE2[Save InferenceCache TTL 5min]
    CACHE2 --> HYDRATE[Hydrate ProductProjection]
    HYDRATE --> TOP[Top limit products]
```

**Trạng thái model-serving:** Mock — không ảnh hưởng UI chính.

### 3.13.10 Action weights mặc định

Từ `behavior_actions.py` / `DEFAULT_ACTION_WEIGHTS`:

| Action | Weight |
|--------|--------|
| purchase | 5.0 |
| add_to_cart | 3.0 |
| review | 2.0 |
| wishlist | 2.0 |
| click | 1.0 |
| view | 1.0 |
| search | 0.5 |
| remove_from_cart | -1.0 |

Weights này dùng cho behavior scoring trong repository, đồng bộ với `RAGSystem` action_weights.

### 3.13.11 Bảng tổng hợp trọng số hybrid

| Tầng | Env variable | Default |
|------|--------------|---------|
| Matrix CF | `IMPLICIT_CF_ALS_WEIGHT` | 4.0 |
| Co-occurrence | `COOCCURRENCE_WEIGHT` | 3.0 |
| Co-purchase | `COPURCHASE_WEIGHT` | 2.5 |
| Category | `CATEGORY_AFFINITY_WEIGHT` | 2.0 |
| Purchase category boost | `PURCHASE_CATEGORY_WEIGHT` | 8.0 |
| Global popularity | `GLOBAL_POPULARITY_WEIGHT` | 1.5 |
| Item CF popularity | `ITEM_CF_POPULARITY_WEIGHT` | 1.0 |
| BiLSTM bias range | — | 0.75 – ~1.25 |

### 3.13.12 Ví dụ walkthrough cụ thể

**Giả sử** `customer_id=42`, BiLSTM dự đoán `{action: purchase, confidence: 0.8}`, đã mua sản phẩm {10}, behavior scores cao ở sản phẩm {15, 20}.

1. `behavior_bias` = 1.0 + 0.2 = 1.2
2. NMF gợi ý {25, 30} → score += 4.0 × 1.2 × normalize
3. Co-occurrence từ seed {15,20,10} → {25, 33} score += 3.0 × 1.2
4. Co-purchase từ order → {40} score += 2.5
5. Category affinity (fashion) → {50, 51} score += 2.0 × 1.2
6. Loại {10} đã mua
7. Sort → Top 10 [25, 33, 50, 30, 40, ...]
8. `save_log()` + trả về API

### 3.13.13 Đánh giá nội bộ pipeline

**Ưu điểm thiết kế:**
- Multi-signal — không phụ thuộc một model.
- Cold start có xử lý rõ (`random-cold-start`).
- BiLSTM gắn trực tiếp business logic (bias), không chỉ metric.

**Hạn chế:**
- Không có learning-to-rank end-to-end.
- Trọng số env manual — chưa auto-tune.
- Neo4j chưa merge vào luồng chính UI.

### Nhận xét mục 3.13

AI Recommender System của đồ án là **hybrid engine thực chiến** trong `RecommenderService`, không phải wrapper gọi API ngoài. Đọc xong mục 3.13, giảng viên có thể trace từ `BehaviorEvent` → `score_map` → `recommended_product_ids` hoàn toàn trong source code."""

SEC_314 = r"""## 3.14 ĐÁNH GIÁ AI-SERVICE

### 3.14.1 Ưu điểm

| STT | Ưu điểm | Căn cứ source code |
|-----|---------|-------------------|
| 1 | Kiến trúc lai đa tín hiệu | 6 tầng scoring + BiLSTM bias |
| 2 | RAG bám catalog thật | `product-service` live fetch |
| 3 | Graph cập nhật realtime | `EventHandler._update_neo4j_graph` |
| 4 | Tích hợp UI hoàn chỉnh | chat widget + home recommendations |
| 5 | MLOps schema sẵn | `ModelVersion`, `InferenceCache`, `InferenceMetric` |
| 6 | Fallback graceful | Groq fallback, SVD embedding fallback, cold-start random |
| 7 | Đồng stack Django | Dễ maintain cùng team backend |
| 8 | Artifact BiLSTM có metric | 77.3% accuracy documented |

### 3.14.2 Nhược điểm

| STT | Nhược điểm | Chi tiết |
|-----|------------|----------|
| 1 | Training BiLSTM không trong repo | Khó reproduce từ zero |
| 2 | model-serving mock | MLOps pipeline chưa hoàn chỉnh |
| 3 | Hai graph không thống nhất | NetworkX vs Neo4j property names |
| 4 | Không có vector DB scale lớn | Pickle in-memory |
| 5 | Review text chưa vào KB | Mất tín hiệu sentiment |
| 6 | faiss/openai deps thừa | Gây hiểu nhầm |
| 7 | GNN stub không chạy | `data_sync` missing |
| 8 | Phụ thuộc Groq API | Cần internet + API key |

### 3.14.3 Khả năng mở rộng

| Hướng | Khả thi | Ghi chú |
|-------|---------|---------|
| Thêm SKU 10k→100k | Cần FAISS/Milvus | Dependency faiss đã có |
| Real-time train NMF | Đã có command | Chưa schedule tự động |
| GPU inference | Cần NVIDIA runtime | Hiện CPU-only |
| Multi-region | Chưa | Single docker-compose |
| Seller AI portal | **Không có UI** | Chỉ customer-facing |

### 3.14.4 Khả năng triển khai thực tế

- **Docker Compose:** Sẵn sàng demo đồ án.
- **Production cloud:** Cần secrets management `GROQ_API_KEY`, Neo4j backup, Redis persistence.
- **Monitoring:** `InferenceMetric`, JSON logging qua `common/middleware.py` — Jaeger có trong hệ thống tổng thể.

### 3.14.5 Khả năng nâng cấp

| Upgrade | Effort | File impact |
|---------|--------|-------------|
| Thay Groq → OpenAI | Thấp | `rag_llm.py` |
| Wire FAISS index | Trung bình | `hybrid_retriever.py` |
| Real model-serving | Cao | `model-serving-service/app/main.py` |
| Fine-tune embedding | Trung bình | sentence-transformers |
| GraphRAG thống nhất | Cao | Neo4j + RAGSystem merge |

### 3.14.6 Chi phí vận hành

| Hạng mục | Chi phí |
|----------|---------|
| Groq API | Free tier / pay per token |
| Neo4j Community | Miễn phí license |
| CPU RAM | ~2–4GB cho recommender container (embedding model) |
| GPU | Không bắt buộc hiện tại |
| DevOps | 1 compose stack — phù hợp đồ án |

### 3.14.7 Hiệu năng

| Thành phần | Latency ước tính | Bottleneck |
|------------|------------------|------------|
| Hybrid recommend | < 500ms | product-service fetch + DB |
| BiLSTM inference | < 100ms | TensorFlow CPU |
| Chat RAG end-to-end | 2–20s | Groq API + embedding |
| build_catalog_index | vài giây–phút | Số lượng SKU |
| Neo4j MERGE | < 50ms/event | Graph size |

### 3.14.8 Kết luận chương

Chương 3 đã trình bày **toàn bộ AI-Service** từ phân tích yêu cầu (3.1), kiến trúc (3.2), Knowledge Base (3.3), vector retrieval (3.4), RAG (3.5), GraphRAG (3.6), Neo4j (3.7), Deep Learning BiLSTM (3.8), thực nghiệm (3.9), triển khai (3.10), tích hợp chat+DL (3.11), tích hợp e-commerce UI (3.12), recommender pipeline chi tiết (3.13), đến đánh giá (3.14).

**Thông điệp cốt lõi cho giảng viên:** Hệ thống AI của đồ án không phải một model đơn lẻ mà là **chuỗi pipeline có thể kiểm chứng** — mỗi bước có file Python, endpoint, hoặc artifact tương ứng. Khi đọc mã, hãy bắt đầu từ `RAGChatLLM.chat()` (chat) và `RecommenderService.recommend()` (gợi ý) — hai entry point bao trùm 90% giá trị AI phía người dùng.

---

*Tài liệu được đối chiếu với repository tại thời điểm viết. Các thành phần đánh dấu "Không tìm thấy trong source code dự án" cần được làm rõ khi bảo vệ đồ án trước hội đồng.*"""
