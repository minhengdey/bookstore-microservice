# -*- coding: utf-8 -*-
"""Supplementary expansion blocks to reach chapter length target."""

# Appended to SEC_38 in generator
SEC_38_EXPAND = r"""
### 3.8.4 Chi tiết kiến trúc BiLSTM v5 (từ artifact `model_best.keras`)

Phần này mô tả kiến trúc **đã deploy** — đối chiếu `inference_utils.py` và `models/model_best_evaluation.txt`. Script `train_models_v5.py` được nhắc trong evaluation file: **Không tìm thấy trong source code dự án** (train offline, copy artifact vào repo).

```mermaid
graph TD
    subgraph INPUT["Input Layer"]
        I1["Input shape: (20, 18)"]
        I2[LayerNormalization]
    end

    subgraph BILSTM1["BiLSTM Layer 1"]
        B1F[LSTM Forward 256]
        B1B[LSTM Backward 256]
        B1C[Concatenate 512 dims]
        B1N[LayerNormalization]
        B1D[Dropout 0.30]
    end

    subgraph BILSTM2["BiLSTM Layer 2"]
        B2F[LSTM Forward 128]
        B2B[LSTM Backward 128]
        B2C[Concatenate 256 dims]
    end

    subgraph ATTENTION["Multi-Head Self-Attention"]
        A1["4 heads, d_model=256"]
        A2[Scaled Dot-Product]
    end

    subgraph OUTPUT["Output"]
        POOL[GlobalAveragePooling1D]
        D1[Dense 256 GELU]
        D2[Dense 128 GELU]
        D3[Dense 8 Softmax]
    end

    I1 --> I2 --> B1F & B1B --> B1C --> B1N --> B1D
    B1D --> B2F & B2B --> B2C --> A1
    B2C --> POOL --> D1 --> D2 --> D3
```

#### Tại sao chọn BiLSTM cho hành vi mua sắm?

Hành vi mua sắm là chuỗi thời gian có **phụ thuộc hai chiều**:
- **Forward:** view → click → add_to_cart thể hiện intent tăng dần.
- **Backward:** Biết kết quả cuối là `purchase` giúp hiểu các bước trước thuộc "buying journey".

LSTM một chiều chỉ nhìn quá khứ. BiLSTM trong `model_best.keras` đọc cả hai hướng — phù hợp session e-commerce 20 bước (`SEQ_LEN=20` trong `encoders.pkl`).

#### Multi-Head SelfAttention — code production

Custom layer **bắt buộc** khi load model — định nghĩa trong `inference_utils.py`:

```python
@tf.keras.utils.register_keras_serializable(package="Custom", name="MultiHeadSelfAttention")
class MultiHeadSelfAttention(tf.keras.layers.Layer):
    def __init__(self, d_model: int, num_heads: int, **kwargs):
        super().__init__(**kwargs)
        self.d_model = d_model
        self.num_heads = num_heads
        self.depth = d_model // num_heads
        self.Wq = tf.keras.layers.Dense(d_model, name="Wq")
        self.Wk = tf.keras.layers.Dense(d_model, name="Wk")
        self.Wv = tf.keras.layers.Dense(d_model, name="Wv")
        self.out = tf.keras.layers.Dense(d_model, name="out")

    def call(self, x):
        q = self.split_heads(self.Wq(x))
        k = self.split_heads(self.Wk(x))
        v = self.split_heads(self.Wv(x))
        dk = tf.cast(tf.shape(k)[-1], tf.float32)
        scores = tf.matmul(q, k, transpose_b=True) / tf.math.sqrt(dk)
        weights = tf.nn.softmax(scores, axis=-1)
        context = tf.matmul(weights, v)
        # ... reshape + self.out(context)
```

**Giải thích cho người mới:** Attention gán "điểm chú ý" cho từng bước trong chuỗi. Bước `add_to_cart` gần đây thường có weight cao hơn `search` từ 15 bước trước — model tự học qua training, không hard-code.

### 3.8.5 Feature Engineering — 18 features/timestep

| Nhóm | Chiều | Mô tả | Nguồn runtime |
|------|-------|-------|---------------|
| One-hot action | 8 | search, view, click, wishlist, add_to_cart, remove_from_cart, purchase, review | `encoders.pkl` ACTIONS |
| category_code | 1 | Danh mục chuẩn hóa | product-service metadata |
| device_code | 1 | mobile/tablet/desktop | BehaviorEvent |
| price_tier | 1 | low/mid/high | `_price_tier()` ngưỡng 100k/300k |
| hour_norm | 1 | Giờ/23 | timestamp event |
| dow_norm | 1 | Thứ/6 | timestamp event |
| product_norm | 1 | product_id encoded | LabelEncoder |
| recency | 1 | Vị trí trong cửa sổ 0→1 | sequence index |
| purchase_norm | 1 | Lịch sử mua chuẩn hóa | aggregate DB |
| step_ratio | 1 | Bước/session length | session group |
| goal_code | 1 | browsing/buying/... | `_goal_from_action()` |

**Tổng: 18** — ghi trong `encoders.pkl` key `N_FEAT=18`.

### 3.8.6 Kỹ thuật huấn luyện (offline — từ evaluation file)

| Kỹ thuật | Tham số | Mục đích |
|----------|---------|----------|
| Label smoothing | ε=0.10 | Giảm overconfidence |
| Gradient clipping | norm=1.0 | Ổn định BiLSTM |
| Warmup LR | 1e-5 → 3e-4 (5 epoch) | Tránh diverge đầu train |
| Cosine decay | về 0 | Fine-tune cuối |
| EarlyStopping | patience=6 | Chọn epoch tốt |
| Dropout | 0.30 sau BiLSTM1 | Chống overfit |
| Oversampling | rare class ×4 | Cân bằng review, wishlist |
| Stratified split | 70/15/15 | Giữ phân phối class |

**train_models_v5.py, train_hyper_search.py:** Không tìm thấy trong source code dự án.

### 3.8.7 So sánh GRU / LSTM / BiLSTM (bảng đầy đủ)

| Model | Accuracy | F1-macro | F1-weighted | Epochs | Thời gian train |
|-------|----------|----------|-------------|--------|-----------------|
| GRU | 0.6274 | 0.6018 | 0.6203 | 45 | ~12,000s (ước tính) |
| LSTM | 0.6930 | 0.6826 | 0.6927 | 45 | ~18,000s |
| **BiLSTM** | **0.7730** | **0.7598** | **0.7703** | **45** | **39,602s** |

**Composite score** (0.5×Acc + 0.5×F1-macro): BiLSTM = **0.7664** — cao nhất, chọn deploy.

### 3.8.8 Thí nghiệm v6 (tham khảo — không deploy)

Các kiến trúc NCF, GRU4Rec, SASRec, BERT4Rec, LightGCN, DIN được mô tả trong tài liệu phát triển trước đó. **Không tìm thấy `train_models_v6.py` trong source code dự án.**

| Model | Accuracy | Ghi chú |
|-------|----------|---------|
| DIN | 1.0000 | Data leakage — target item = label |
| GRU4Rec | ~0.6355 | Embedding-only, thấp hơn v5 |
| BiLSTM_Attn (v6) | ~0.6351 | Không có 18 manual features |
| SASRec/BERT4Rec | ~0.6342 | Transformer session |

**Kết luận:** BiLSTM v5 với feature engineering phong phú vượt embedding-only v6 (~77% vs ~63%). DIN bị loại vì leakage.

### 3.8.9 Inference — hàm `predict()` từng bước

1. `BehaviorPredictionService.predict_next_action(customer_id)` query `BehaviorEvent.objects.filter(customer_id=).order_by('-timestamp')[:20]`.
2. Với mỗi event, gọi `product-service` lấy category + price (cache `_product_cache`).
3. Build DataFrame, encode qua `UserBehaviorPredictor._build_sequence()`.
4. `model.predict(x, verbose=0)` → softmax 8 class.
5. `action = ACTIONS[argmax]`, `confidence = max(prob)`.
6. Trả JSON cho API và `RecommenderService._behavior_bias()`.

**Latency:** TensorFlow CPU ~5–50ms tùy máy — phù hợp realtime recommendation."""

SEC_313_EXPAND = r"""
### 3.13.14 Phân tích mã nguồn `RecommenderService.recommend()` từng dòng logic

Để giảng viên có thể mở file và đối chiếu, dưới đây là trình tự **đúng thứ tự code** (`app/services/recommender_service.py`):

**Bước A — Khởi tạo context**
```python
catalog = ProductCatalog.get_products()
active_product_ids = set(catalog.keys())
prediction = self.predict_next_action(customer_id)
behavior_bias = self._behavior_bias(prediction_action, prediction_confidence)
purchased = self._get_customer_products(customer_id) & active_product_ids
interacted = self.repo.get_interacted_product_ids(customer_id) & active_product_ids
exclude = purchased  # chỉ ẩn đã mua, vẫn gợi ý đã xem
```

**Bước B — Cold start gate**
```python
if not self.repo.has_behavior_history(customer_id):
    rng = random.Random(customer_id)
    rng.shuffle(candidates)
    return recommended, "random-cold-start", scores
```
*Giải thích:* `Random(customer_id)` đảm bảo cùng user luôn thấy cùng thứ tự random trong session — tránh "nhảy" layout mỗi refresh.

**Bước C — Tích lũy điểm**
```python
score_map: dict[int, float] = {}
self._blend_matrix_cf(...)      # weight 4.0 × behavior_bias
# co-occurrence weight 3.0
# copurchase weight 2.5
# category affinity weight 2.0, purchase boost 8.0
# global popularity 1.5
# item CF popularity 1.0
```

**Bước D — Penalty & sort**
```python
for pid in browsed_not_bought:
    if cat_id not in purchase_categories:
        score_map[pid] *= 0.45
ranked = sorted(score_map.items(), key=lambda x: x[1], reverse=True)
```

**Bước E — Logging**
```python
self.repo.save_log(customer_id, recommended, strategy="+".join(strategy_parts))
```

### 3.13.15 `ImplicitCFEngine` — Collaborative Filtering chi tiết

**Train (offline command `train_implicit_cf_local`):**
1. Đọc `BehaviorEvent` + orders, build sparse matrix user×item.
2. `sklearn.decomposition.NMF(n_components=64, max_iter=200)`.
3. Lưu `factors.npz` (W, H), `interactions.npz`, `meta.json` (user_id_to_idx, idx_to_product_id, product_id map).

**Inference:**
```python
scores = (self._W[uidx] @ self._H).ravel()
# Mask items already interacted: scores[j] = -inf
top_indices = np.argpartition(scores, -limit)[-limit:]
```

**Mapping ID:** `dataset_product_id_to_local_product_id` trong `meta.json` — quan trọng khi train từ `data_user500.csv` nhưng serve `product-service` integer IDs (`product_id_map.json`).

### 3.13.16 `RecommenderRepository` — SQL patterns

Repository pattern **chỉ** dùng cho recommender (`app/repositories/recommender_repository.py`):

| Query logic | Mục đích |
|-------------|----------|
| `BehaviorEvent.filter(customer_id).values('product_id').annotate(score=Sum(weight))` | behavior_scores |
| Co-occurrence: join behaviors của users khác có overlap product | item similarity |
| `RecommendationLog` insert | audit trail |

### 3.13.17 Intent-based recommendation trong chat (nhánh phụ)

Khi user chat "gợi ý đồ công nghệ", `RAGChatLLM._resolve_products_for_intent()` ưu tiên:
- `RECOMMEND` intent → `cf_products` từ `RecommenderService`
- `SEARCH` intent → `search_products` từ hybrid retriever
- `FOLLOW_UP` → ghép history + price filter `_apply_price_filter()`

Đây là **personalization qua ngôn ngữ** — cùng engine recommendation nhưng routing khác theo intent.

### 3.13.18 RabbitMQ → Recommendation feedback loop

`consume_events` command (`app/management/commands/consume_events.py`):
- Catalog update → `ProductProjection` → hydrate recommendation
- Interaction → `BehaviorEvent` + Neo4j + Redis → ảnh hưởng lần recommend tiếp theo
- Payment → PURCHASE edge weight 10.0 → mạnh nhất trong graph

```mermaid
sequenceDiagram
    participant RMQ as RabbitMQ
    participant RC as recommender-consumer
    participant EH as EventHandler
    participant PG as recommender_db
    participant N4 as Neo4j
    participant RS as RecommenderService

    RMQ->>RC: interaction.view
    RC->>EH: handle_interaction_event
    EH->>PG: UserSequenceEvent + BehaviorEvent
    EH->>N4: MERGE VIEW edge
    Note over RS: Lần GET /recommendations/ tiếp theo
    RS->>PG: đọc behavior mới
    RS-->>RS: score_map thay đổi
```

### 3.13.19 API Contract đầy đủ

**GET `/recommendations/<customer_id>/`**
```json
{
  "customer_id": 1,
  "recommended_product_ids": [12, 45, 78],
  "recommendation_scores": [{"product_id": 12, "score": 8.4521}],
  "next_action_prediction": {
    "action": "add_to_cart",
    "confidence": 0.734,
    "probabilities": {"view": 0.05, "add_to_cart": 0.73, "...": "..."}
  },
  "strategy": "hybrid+cf+cooccurrence+category+global-popularity"
}
```

**POST `/api/recommender/events/`** — body từ `behavior_tracking`:
```json
{
  "customer_id": 1,
  "product_id": 12,
  "action": "view",
  "session_id": "sess-abc",
  "metadata": {"page": "product_detail"}
}
```

### 3.13.20 Ma trận chiến lược (strategy) và ý nghĩa

| strategy fragment | Khi xuất hiện | Ý nghĩa |
|-------------------|---------------|---------|
| `hybrid` | Luôn | Pipeline chính |
| `cf` | User có trong NMF matrix | Matrix factorization có đóng góp |
| `cooccurrence` | Có user tương tự | Collaborative từ behavior |
| `copurchase` | Có order history | Market basket |
| `category` | category_affinity không rỗng | Content-based |
| `purchase-category` | Đã mua trước đó | Boost category đã mua |
| `global-popularity` | Fallback signal | Trending toàn site |
| `item-popularity` | Item trong CF matrix | Popular trong latent space |
| `random-cold-start` | Không có history | Chưa personalize được |

### 3.13.21 Câu hỏi thường gặp (FAQ kỹ thuật cho bảo vệ đồ án)

**H: Tại sao không dùng một mô hình end-to-end?**  
Đ: Dữ liệu sparse (nhiều user ít event), cold start phổ biến — hybrid cho phép từng tín hiệu bù trừ. Code thể hiện rõ: CF fail → vẫn còn category + popularity.

**H: BiLSTM train trên user thật hay CSV?**  
Đ: Artifact train từ `data_user500.csv` (offline). Inference trên user thật qua `BehaviorEvent` — cùng schema feature nhờ `normalize_action()` và product metadata enrich.

**H: Neo4j có ảnh hưởng trang chủ không?**  
Đ: Trực tiếp **không** trong `RecommenderService`. Gián tiếp qua events cập nhật behavior trong PostgreSQL — cùng nguồn với BiLSTM và co-occurrence SQL.

**H: Làm sao đánh giá recommendation offline?**  
Đ: Schema `RecommendationFeedback` + `ModelMetric.ndcg_at_k` — cần thu thập click qua `POST /api/v1/recommendations/feedback`. **Chưa có dataset feedback cố định trong repo.**"""

SEC_35_EXPAND = r"""
### 3.5.9 System Prompt Mochi và Prompt Engineering

`RAGChatLLM` sử dụng system prompt tiếng Việt định nghĩa persona **Mochi** — trợ lý mua sắm thân thiện. Prompt yêu cầu:
- Trả lời ngắn gọn, có emoji vừa phải
- **Bắt buộc** dùng link markdown `[Tên](/products/{id}/)` cho mỗi sản phẩm gợi ý
- Không bịa giá — chỉ dùng giá trong `suggested_products`
- Tôn trọng `intent` và `next_action_prediction`

**Cấu trúc messages gửi Groq:**
```python
messages = [
  {"role": "system", "content": system_prompt},
  # history tối đa 10 turns
  {"role": "user", "content": user_message},
]
```

### 3.5.10 Intent Router — bảng pattern đầy đủ

| Intent | Pattern ví dụ (regex) | Hành vi retrieval |
|--------|----------------------|-------------------|
| POLICY | đổi trả, giao hàng, COD | `_policy_context()` |
| GREETING | xin chào, hello | Chào + gợi ý hot |
| RECOMMEND | gợi ý, đề xuất, bán chạy | Ưu tiên RecommenderService |
| SEARCH | tìm, mua, son, laptop | Ưu tiên hybrid_search |
| COMPARE | so sánh, tốt hơn | So sánh trong prompt |
| FOLLOW_UP | rẻ hơn, còn hàng, màu | Ghép history 3 turn |

File: `rag/intent_router.py` — **rule-based**, không dùng ML classifier (latency thấp, deterministic).

### 3.5.11 Fallback khi Groq không khả dụng

`_local_fallback_answer()` tạo câu trả lời template từ `live_products` — vẫn có link sản phẩm. Điều kiện: `GROQ_API_KEY` rỗng hoặc HTTP error.

### 3.5.12 `hybrid_search()` — pseudocode đầy đủ

```python
def hybrid_search(query, top_k=5):
    self.ensure_index()
    q_sparse = self._tfidf.transform([query])
    sparse_scores = cosine_similarity(q_sparse, self._tfidf_matrix).ravel()
    q_dense = self._encoder.encode([f"query: {query}"], normalize_embeddings=True)
    dense_scores = cosine_similarity(q_dense, self._embeddings).ravel()
    fused = reciprocal_rank_fusion(sparse_rank, dense_rank, k=60)
    candidates = top_n(fused, RERANK_CANDIDATES=20)
    return reranker.rerank(query, candidates)[:top_k]
```

### 3.5.13 RAG vs Fine-tune LLM — vì sao đồ án chọn RAG?

| Tiêu chí | RAG (đã chọn) | Fine-tune LLM |
|----------|---------------|---------------|
| Cập nhật giá mới | Rebuild index nhanh | Phải train lại |
| Chi phí | Groq API + CPU embedding | GPU + dataset lớn |
| Hallucination | Giảm nhờ context | Vẫn có rủi ro |
| Triển khai đồ án | Đủ trong docker compose | Phức tạp hơn |

**Fine-tune LLM trên catalog:** Không tìm thấy trong source code dự án."""

SEC_33_EXPAND = r"""
### 3.3.6 Đồng bộ Knowledge Base với event-driven architecture

```mermaid
sequenceDiagram
    participant PS as product-service
    participant RMQ as RabbitMQ
    participant RC as recommender-consumer
    participant EH as EventHandler
    participant IDX as build_catalog_index
    participant PKL as catalog_hybrid_index.pkl

    PS->>RMQ: catalog.product.updated
    RMQ->>RC: event payload
    RC->>EH: handle_catalog_event
    EH->>EH: ProductProjection ORM update
    Note over IDX: Entrypoint định kỳ hoặc startup
    IDX->>PS: GET /products/ paginated
    IDX->>PKL: TF-IDF + embeddings save
```

### 3.3.7 Bảng ánh xạ Entity → KB storage

| Entity | PostgreSQL | Pickle Index | Neo4j | Redis |
|--------|------------|--------------|-------|-------|
| Product | ProductProjection | catalog[] | Product node | trending zset |
| User | UserProjection | — | User node | user_sequence list |
| Category | category_id in projection | trong doc text | Category node (bulk) | — |
| Behavior | BehaviorEvent | — | edges | sequence JSON |
| Order | — (query order-service) | — | — | — |

### 3.3.8 Chất lượng dữ liệu và validation

| Rule | Implementation |
|------|----------------|
| Không double-count PURCHASE | Chặn từ interaction stream |
| Out-of-order events | `projection_version` check |
| Product ID map | `product_id_map.json` cho CSV→local |
| Empty catalog guard | `recommend()` trả `empty-catalog` |

### 3.3.9 FAQ Knowledge (Policy KB)

`_policy_context()` trong `rag_llm.py` cung cấp text chính sách đổi trả, giao hàng khi `intent=POLICY`. **Không có bảng FAQ trong database** — cập nhật policy cần sửa code hoặc mở rộng sang CMS sau này."""

SEC_314_EXPAND = r"""
### 3.14.9 Bảng đối chiếu yêu cầu đồ án vs thực tế triển khai

| Yêu cầu / Thành phần | Trạng thái | Ghi chú |
|---------------------|------------|---------|
| Chatbot AI (Mochi) | ✅ Hoàn chỉnh | Groq + RAG |
| Recommendation hybrid | ✅ Hoàn chỉnh | RecommenderService |
| BiLSTM next-action | ✅ Inference | Train script ngoài repo |
| RAG | ✅ Hoàn chỉnh | hybrid_retriever |
| GraphRAG | ✅ Một phần | NetworkX + Neo4j tách biệt |
| Neo4j | ✅ Runtime MERGE | Bulk + realtime |
| Knowledge Base | ✅ Catalog index | KB folder trống |
| Vector DB ChromaDB | ❌ Không có | Dùng pickle |
| FAISS | ❌ Chưa dùng | Chỉ requirements |
| Fine-tune LLM | ❌ Không có | |
| GNN production | ❌ Stub | gnn_pipeline.py |
| model-serving thật | ❌ Mock | FastAPI skeleton |
| Seller AI UI | ❌ Không có | |
| Elasticsearch AI | ❌ Không có | |

### 3.14.10 Hướng phát triển sau đồ án

1. Wire FAISS vào `HybridProductRetriever` cho catalog 100k+ SKU.
2. Thay mock `model-serving` bằng TensorFlow Serving hoặc TorchServe cho BiLSTM.
3. Thống nhất Neo4j schema (`id` vs `user_id`).
4. Đưa review text vào KB qua interaction-service pipeline.
5. Thu thập `RecommendationFeedback` để tính NDCG online thật."""

SEC_312_EXPAND = r"""
### 3.12.7 Chi tiết `chatbot-widget.js` — tích hợp frontend

```javascript
const apiUrl = `${hostUrl}/ai/chat/`;  // same-origin proxy

// Gửi request
const payload = {
    message: text,
    user_id: userId,
    history: chatHistory,
    recent_behaviors: JSON.parse(sessionStorage.getItem("mochi_recent_behaviors") || "[]")
};
const res = await fetch(apiUrl, { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload) });
```

**Behavior tracking local:** Khi pathname match `/products/(\d+)/`, lưu `view_product_{id}` vào `sessionStorage` (tối đa 5 items) — feed vào RAG qua `recent_behaviors`.

### 3.12.8 `ai_chat_proxy` — gateway code path

```python
# api-gateway/gateway/views.py (tóm tắt)
@csrf_exempt
def ai_chat_proxy(request):
    recommender_url = f"{SVC['recommender']}/api/recommender/chat-ktmp"
    for attempt in range(1, 4):
        resp = requests.post(recommender_url, json=body, timeout=90)
```

**Lý do proxy:** Giấu `GROQ_API_KEY` (nằm ở recommender env), đồng nhất origin, thêm retry.

### 3.12.9 `home-storefront.js` — recommendation UI

Trang chủ fetch recommendations khi user đã login — hiển thị carousel sản phẩm gợi ý. Product card link tới `/products/{id}/` — đóng vòng với behavior tracking.

### 3.12.10 Luồng dữ liệu UI → AI → UI (end-to-end)

| Bước | Thành phần | Dữ liệu |
|------|------------|---------|
| 1 | User mở trang chủ | cookie session auth |
| 2 | JS fetch recommendations | customer_id từ template |
| 3 | RecommenderService | product_ids |
| 4 | Template render cards | HTML + ảnh từ product-service |
| 5 | User click sản phẩm | behavior event |
| 6 | Lần sau recommend tốt hơn | BehaviorEvent updated |"""

SEC_36_EXPAND = r"""
### 3.6.8 Thuật toán `RAGSystem.recommend_products()` — chi tiết

1. `retrieve_user_history(user_id, 10)` — duyệt edge `PERFORMED` trên NetworkX, sort timestamp.
2. Đếm category frequency → `favorite_category` + top 3 categories.
3. **Quota diversification:**
   - 60% slots từ category chính
   - 30% từ category phụ
   - 10% exploration categories khác
4. Mỗi category gọi `retrieve_popular_in_category()` — **bỏ super-nodes**.
5. Trả `recommendations` list dict với `product_id`, `product_name`, `interactions` score.

### 3.6.9 Jaccard Similarity trên đồ thị

```python
overlap = len(user_products & other_products)
union = len(user_products | other_products)
score = overlap / union if union else 0
```

Chỉ tính trên sản phẩm `purchase` và `add_to_cart`, loại super-node — tránh "ai cũng giống nhau vì cùng xem iPhone".

### 3.6.10 GraphRAG trong academic literature vs đồ án

Trong literature, GraphRAG (Microsoft) thường gồm: extract entities → build graph → community detection → summarize communities → retrieve. **Đồ án không triển khai community summarization LLM** — thay bằng:
- Direct neighbor retrieval (`retrieve_user_history`)
- Neo4j multi-hop CF (`RecommendationPipeline`)
- Inject vào prompt dạng text thô

Đây là **GraphRAG pragmatic** phù hợp quy mô đồ án."""

SEC_37_EXPAND = r"""
### 3.7.8 Truy vấn nâng cao (`scripts/neo4j_advanced_queries.cypher`)

File script hỗ trợ:
- Chuẩn hóa trọng số edge
- Lọc super-node (product có degree > percentile)
- Item-based CF mở rộng
- GDS optional (nếu cài plugin) — **plugin không có trong docker-compose mặc định**

### 3.7.9 `GraphRepository` JSON (`app/services/graph/`)

```python
# schema.py — GraphNode, GraphEdge dataclasses
# repository.py — lưu data/graph_kb.json
```

**Không wired vào RAGChatLLM hay RecommenderService** — module độc lập, có thể dùng export snapshot kiến thức."""

# Map section -> expansion (defined after all SEC_*_EXPAND blocks)
EXPANSIONS = {
    "SEC_33": SEC_33_EXPAND,
    "SEC_35": SEC_35_EXPAND,
    "SEC_36": SEC_36_EXPAND,
    "SEC_37": SEC_37_EXPAND,
    "SEC_38": SEC_38_EXPAND,
    "SEC_312": SEC_312_EXPAND,
    "SEC_313": SEC_313_EXPAND,
    "SEC_314": SEC_314_EXPAND,
}

SEC_APPENDIX = r"""
---

## PHỤ LỤC CHƯƠNG 3 — THAM CHIẾU MÃ NGUỒN NHANH

### P.1 Danh sách endpoint AI-Service đầy đủ

| Method | Path | File view |
|--------|------|-----------|
| POST | `/api/recommender/chat-ktmp` | `rag_views.KTMPChatConsultingView` |
| POST | `/chatbot/` | alias |
| GET | `/recommendations/<customer_id>/` | `recommender_views.RecommendationView` |
| GET | `/recommend` | `RecommendAliasView` |
| GET | `/api/recommender/next-action/<customer_id>/` | `NextActionPredictionView` |
| POST | `/api/recommender/events/` | `BehaviorEventView` |
| GET | `/api/v1/recommendations/personal` | `api.get_personal` |
| GET | `/api/v1/recommendations/trending` | `api.get_trending` |
| POST | `/api/v1/recommendations/feedback` | `api.track_feedback` |
| GET/POST | `/api/v1/models/*` | `admin_api.py` |

### P.2 ORM Models trong `recommender_db`

| Model | File | Vai trò |
|-------|------|---------|
| BehaviorEvent | `behavior_event.py` | Hành vi gốc cho DL + CF |
| RecommendationLog | `recommendation_log.py` | Audit recommendations |
| UserProjection | `projection.py` | Read model user |
| ProductProjection | `projection.py` | Read model product |
| UserSequenceEvent | `projection.py` | Backup sequence |
| ModelVersion | `model_registry.py` | A/B routing |
| ModelMetric | `metrics.py` | CTR, NDCG |
| InferenceMetric | `metrics.py` | Latency tracking |
| InferenceCache | `metrics.py` | 5-min TTL cache |
| RecommendationFeedback | `metrics.py` | Online metrics |
| UserFeature / ProductFeature | `feature_store.py` | Embedding placeholder |

### P.3 Dependencies AI (`requirements.txt` chọn lọc)

| Package | Dùng thực tế? |
|---------|---------------|
| tensorflow | ✅ BiLSTM |
| sentence-transformers | ✅ Embedding |
| scikit-learn | ✅ TF-IDF, NMF |
| networkx | ✅ RAGSystem |
| neo4j | ✅ EventHandler |
| numpy, scipy, pandas | ✅ |
| faiss-cpu | ❌ Không import |
| openai, anthropic, groq SDK | ❌ Dùng urllib Groq |

### P.4 `entrypoint.sh` — khởi động container

1. Chờ PostgreSQL ready (`wait-for-it` / custom script)
2. `python manage.py migrate`
3. `sync_purchase_behaviors` + `sync_interaction_behaviors`
4. `ensure_recommender_models` — train NMF nếu thiếu `factors.npz`
5. `build_catalog_index` — TF-IDF + embedding pickle
6. Cron jobs (nếu có) + `runserver 0.0.0.0:8000`

### P.5 `AIModelSingleton` — tránh reload model

```python
# app/services/ai_singleton.py
class AIModelSingleton:
    @classmethod
    def get_ktmp_rag_llm(cls):
        # lazy init RAGChatLLM — một instance / process
```

**Lý do:** Load `sentence-transformers` + `model_best.keras` tốn 10–30 giây — singleton giữ warm model trong memory.

### P.6 Checklist đọc source cho giảng viên

1. Bắt đầu `rag/rag_llm.py` method `chat()` — hiểu chat flow.
2. Đọc `app/services/recommender_service.py` method `recommend()` — hiểu gợi ý.
3. Đọc `inference_utils.py` class `UserBehaviorPredictor` — hiểu DL.
4. Đọc `app/services/event_handler.py` — hiểu data vào graph.
5. Đọc `docker-compose.yml` services `recommender-ai-service`, `neo4j`, `recommender-consumer`.
6. Mở `api-gateway/static/chatbot-widget.js` — hiểu UI.

### P.7 Glosary thuật ngữ AI trong đồ án

| Thuật ngữ | Định nghĩa ngắn trong context đồ án |
|-----------|--------------------------------------|
| RAG | Retrieve sản phẩm → đưa vào prompt → Groq trả lời |
| GraphRAG | Dùng graph (NetworkX/Neo4j) mở rộng context retrieval |
| CF | Collaborative Filtering — NMF matrix factorization |
| Cold start | User chưa có BehaviorEvent |
| behavior_bias | Hệ số nhân từ BiLSTM vào hybrid scores |
| Mochi | Persona chatbot |
| Hybrid retrieval | TF-IDF + dense embedding + RRF |
| Projection | Bản read-only user/product từ events |
| Outbox | Pattern ở service khác — recommender dùng RabbitMQ trực tiếp |

---

*Kết thúc Chương 3.*
"""

