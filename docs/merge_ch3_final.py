# -*- coding: utf-8 -*-
"""Final expansion to meet chapter length >= Ch2."""
import re
from pathlib import Path

CH3 = Path(__file__).parent / "CHUONG3_TAI_LIEU_AI_SERVICE.md"

FINAL = r"""

---

## PHẦN MỞ RỘNG 3 — HƯỚNG DẪN ĐỌC SOURCE CHO HỘI ĐỒNG (CHI TIẾT TỪNG MODULE)

Phần này viết theo phong cách **giảng dạy** — giả định giảng viên chưa đọc code, cần hiểu từng module AI làm gì, input/output là gì, và gọi module nào tiếp theo.

### HD.1 Module `rag/rag_llm.py` — trái tim chatbot

**Class chính:** `RAGChatLLM`

**Phụ thuộc:**
- `RAGSystem` (NetworkX graph)
- `HybridProductRetriever` (catalog index)
- `RecommenderService` (hybrid gợi ý)
- `call_groq()` (LLM)

**Method `chat(user_id, message, history, recent_behaviors)` — 9 giai đoạn:**

1. **Phân loại intent** — quyết định chiến lược trả lời (tìm kiếm vs gợi ý vs chính sách).
2. **Parse customer_id** — nếu `user_id` là số (ví dụ `"42"`) → user production; nếu `"U001"` → user dataset.
3. **Hybrid search** — truy xuất sản phẩm khớp câu chữ từ catalog index.
4. **Keyword search** — gọi thêm `product-service` search nếu hybrid rỗng.
5. **Price filter** — regex giá trong message ("dưới 200k").
6. **Boost viewed** — ưu tiên sản phẩm user vừa xem (từ `recent_behaviors`).
7. **Collaborative products** — `recommend_with_prediction` hoặc `RAGSystem.recommend_products`.
8. **Build prompt** — ghép context + system prompt Mochi.
9. **Groq + postprocess** — sinh câu trả lời, sửa link.

**Output dict:**
```python
{
  "answer": str,           # Câu trả lời tiếng Việt
  "products": list[dict],  # Top sản phẩm kèm giá/stock
  "intent": str,           # search_product | recommend | ...
  "context_used": str,     # Debug context (có thể ẩn UI)
}
```

### HD.2 Module `rag/hybrid_retriever.py` — động cơ tìm kiếm semantic

**Class:** `HybridProductRetriever`

**Lifecycle:**
- `ensure_index()` — load pickle hoặc rebuild
- `rebuild_index()` — paginate product-service, fit TF-IDF, encode embeddings
- `hybrid_search(query, top_k)` — trả list product dicts

**Tại sao cần cả sparse và dense?**

| Loại | Bắt được | Ví dụ |
|------|----------|-------|
| Sparse TF-IDF | Từ khóa chính xác, SKU | "SKU-ABC123" |
| Dense embedding | Ngữ nghĩa, mô tả dài | "quà tặng cho mẹ thích nấu ăn" |

RRF kết hợp hai ranking không cần chuẩn hóa score — robust khi hai hệ thống cho scale khác nhau.

### HD.3 Module `rag/retriever.py` — GraphRAG offline

**Class:** `RAGSystem`

**Public methods giảng viên cần nhớ:**

| Method | Input | Output |
|--------|-------|--------|
| `retrieve_user_history` | user_id, top_k | List interaction dicts |
| `retrieve_similar_users` | user_id | Jaccard scores |
| `retrieve_popular_in_category` | category | Products không phải super-node |
| `recommend_products` | user_id, top_k | Diversified recommendations |

### HD.4 Module `app/services/recommender_service.py`

**Entry:** `recommend_with_prediction(customer_id, limit)`

**Internal flow:**
```
predict_next_action()
  → recommend(prediction=...)
    → score_map tích lũy 6 nguồn
    → sort → top limit
    → save_log
```

**Điểm quan trọng:** `exclude = purchased` — đã mua không gợi ý lại; đã xem vẫn có thể gợi ý (giảm ×0.45 nếu không cùng category đã mua).

### HD.5 Module `app/services/behavior_prediction_service.py`

**Trách nhiệm:** Bridge giữa Django ORM và TensorFlow model.

**Không train** — chỉ inference. Train artifact nằm ngoài repo.

**Enrich metadata:** Gọi `product-service` vì `BehaviorEvent` có thể thiếu category/price đầy đủ.

### HD.6 Module `inference_utils.py`

**Class:** `UserBehaviorPredictor`

**Contract:**
```python
predictor.predict(sequence: list[dict]) -> {
    "action": str,
    "confidence": float,
    "probabilities": dict[str, float]
}
```

**Custom Keras layer** phải register — nếu thiếu, `load_model` fail.

### HD.7 Module `app/services/event_handler.py`

**Trách nhiệm:** Event-driven sync — biến message queue thành:
- PostgreSQL rows
- Redis lists
- Neo4j edges

**Security note:** Chặn PURCHASE từ interaction stream — chỉ payment event được tạo purchase — tránh gian lận metric.

### HD.8 Module `app/services/recommendation_pipeline.py`

**Dành cho API v1** — không phải homepage path.

**Steps:** A/B model → cache → Neo4j candidates → Redis sequence → model-serving → hydrate → metric.

**Fallback chain:** Neo4j empty → trending Redis → model-serving fail → raw candidates.

### HD.9 Module `model-serving-service/app/main.py`

**Hiện trạng:** Mock — log request, return fake scores.

**Interface chuẩn bị sẵn** cho tương lai load `model_best.keras` hoặc ranker ONNX.

### HD.10 Giải thích thuật toán NMF cho sinh viên không chuyên Toán

Given ma trận R (users × items) với giá trị implicit feedback (view=1, purchase=5...), NMF tìm W và H sao cho R ≈ W×H.

- Mỗi **hàng W** là "vector sở thích" ẩn của user.
- Mỗi **cột H** là "vector thuộc tính" ẩn của item.
- Dự đoán score(user, item mới) = dot(W[user], H[item]).

**Ưu điểm:** Nhanh, scale được hàng nghìn user/item đồ án.
**Nhược điểm:** Cold start user/item mới không có hàng/cột → cần hybrid backup.

### HD.11 Giải thích RAG cho sinh viên không chuyên NLP

**Analogie:** LLM như sinh viên thông minh nhưng **không được phép mở sách** trong kỳ thi. RAG như **được phép xem trang sách liên quan** (catalog retrieval) trước khi trả lời — trả lời dựa trên trích dẫn, không bịa.

### HD.12 Giải thích GraphRAG

**Analogie:** Vector search như tìm theo "mùi văn bản tương tự". Graph như hỏi "khách A và tôi mua chung gì" — collaborative signal vector search khó có.

### HD.13 Bảng câu hỏi thường gặp khi demo chatbot

| Câu hỏi demo | Kỳ vọng | Module xử lý |
|--------------|---------|--------------|
| Xin chào | Chào + gợi ý | GREETING intent |
| Tìm son môi | List son + link | hybrid_search |
| Gợi ý quà tặng | Personalized list | RecommenderService |
| Đổi trả thế nào? | Policy text | POLICY |
| Còn hàng không? | Stock từ live API | _fetch_live_products |
| Rẻ hơn 100k | Price filter | _apply_price_filter |

### HD.14 Bảng metric offline đầy đủ — định nghĩa công thức

**Accuracy (classification):** (số dự đoán đúng) / (tổng mẫu test).

**Precision class k:** TP_k / (TP_k + FP_k) — trong các lần model đoán k, bao nhiêu đúng.

**Recall class k:** TP_k / (TP_k + FN_k) — trong các lần thật là k, model bắt được bao nhiêu.

**F1_k:** 2 × Precision_k × Recall_k / (Precision_k + Recall_k).

**F1-macro:** Trung bình F1 của tất cả class — coi mỗi class quan trọng như nhau (tốt cho imbalance).

**NDCG@K (recommendation):** Đo chất lượng ranking — hit ở vị trí cao được điểm cao hơn. Cần ground truth relevance labels — schema có, data demo chưa đầy đủ.

### HD.15 Ví dụ tính điểm hybrid thủ công (minh họa)

Giả sử `behavior_bias = 1.1`, 2 sản phẩm A và B:

| Nguồn | A | B |
|-------|---|---|
| NMF (w=4) | 2.0 | 0.5 |
| Co-oc (w=3) | 1.0 | 1.5 |
| Category (w=2) | 0.8 | 0.2 |
| **Tổng trước bias** | 3.8 | 2.2 |
| **Sau × bias 1.1** | **4.18** | **2.42** |

→ A xếp trên B. Code thực tế chuẩn hóa từng nguồn trước khi cộng — bảng trên chỉ minh họa ý tưởng.

### HD.16 Docker networking AI services

```
Browser → nginx:80 → api-gateway:8000 → recommender-ai-service:8000 (internal)
recommender-ai-service → product-service:8000
recommender-ai-service → neo4j:7687
recommender-consumer → rabbitmq:5672
```

Port host `8011` map recommender cho debug trực tiếp — production user đi qua gateway.

### HD.17 Environment variables đầy đủ

| Biến | Service | Mô tả |
|------|---------|-------|
| GROQ_API_KEY | recommender | LLM |
| GROQ_MODEL | recommender | Model name |
| PRODUCT_SERVICE_URL | recommender | Catalog |
| ORDER_SERVICE_URL | recommender | Co-purchase |
| NEO4J_URI/USER/PASSWORD | recommender, consumer | Graph |
| REDIS_URL | recommender, consumer | Cache/sequence |
| IMPLICIT_CF_DATA_DIR | recommender | NMF path |
| MODEL_SERVING_URL | consumer | MLOps |
| EMBEDDING_MODEL | recommender | Sentence transformer |
| RECOMMENDER_URL | api-gateway | Proxy target |

### HD.18 Sequence lengths và constants

| Constant | Value | File |
|----------|-------|------|
| SEQ_LEN | 20 | encoders.pkl |
| N_FEAT | 18 | encoders.pkl |
| CHAT_TOP_K | 5 | hybrid_retriever |
| HYBRID_RRF_K | 60 | hybrid_retriever |
| RERANK_CANDIDATES | 20 | hybrid_retriever |
| InferenceCache TTL | 5 min | recommendation_pipeline |
| Redis sequence max | 100 | event_handler |

### HD.19 Lý do chọn Groq thay vì tự host LLM

| Tiêu chí | Groq API | Self-host Llama |
|----------|----------|-----------------|
| GPU server | Không cần | Cần GPU mạnh |
| Latency | Tối ưu LPU | Phụ thuộc hardware |
| Bảo trì | Thấp | Cao |
| Phù hợp đồ án | ✅ | Overkill |

### HD.20 Lý do chọn Neo4j Community

Cypher expressive cho multi-hop queries ("friend-of-friend" shopping). PostgreSQL recursive CTE làm được nhưng code readability thấp hơn cho team đồ án.

### HD.21 Lý do không dùng ChromaDB trong giai đoạn 1

Catalog < 1000 SKU — brute-force cosine trên numpy đủ nhanh (<10ms). ChromaDB thêm operational complexity không cần thiết cho demo.

### HD.22 Roadmap nâng cấp AI (đề xuất sau tốt nghiệp)

**Phase 1 (hiện tại):** Hybrid heuristic + BiLSTM bias + RAG Groq — ✅

**Phase 2:** FAISS index + real model-serving ranker

**Phase 3:** Learning-to-rank (LightGBM) trên features từ hybrid

**Phase 4:** Fine-tune embedding trên click data Việt Nam

**Phase 5:** Graph neural network thay NMF (GNN stub đã có skeleton)

### HD.23 Đạo đức và giới hạn AI trong e-commerce

- Chatbot **không** thay thế hoàn toàn nhân viên cho khiếu nại phức tạp — staff portal vẫn tồn tại.
- Recommendation có thể tạo "filter bubble" — diversification 60/30/10 giảm thiểu.
- Cần thông báo cho user khi dùng AI gợi ý (best practice — UI hiện chưa có banner, ghi nhận cải thiện).

### HD.24 Tóm tắt một trang — Chương 3 cho người bận

**AI-Service làm 3 việc chính:**
1. **Gợi ý sản phẩm** — `RecommenderService` hybrid 6 tầng + BiLSTM bias.
2. **Chat tư vấn** — RAG + Groq, context từ catalog thật.
3. **Ghi nhận & học hành vi** — BehaviorEvent, Neo4j, NMF retrain.

**Dữ liệu vào:** UI events, orders, catalog API, CSV seed.

**Dữ liệu ra:** Top-N product IDs, câu trả lời chat có link, next-action prediction.

**Không có trong repo:** train BiLSTM script, ChromaDB, real model-serving, GNN production.

### HD.25 Cross-reference Chương 2 ↔ Chương 3

| Chương 2 | Chương 3 |
|----------|----------|
| Kiến trúc microservice | AI là một microservice |
| interaction-service | Nguồn behavior events |
| product-service | Nguồn catalog KB |
| api-gateway BFF | Proxy /ai/chat/ |
| Neo4j trong deployment | GraphRAG + MLOps candidates |
| RabbitMQ | recommender-consumer |

### HD.26 Phụ lục — mẫu request/response Postman

**Chat:**
```
POST http://localhost:8000/ai/chat/
Content-Type: application/json

{
  "message": "Gợi ý sản phẩm làm quà",
  "user_id": "1",
  "history": [],
  "recent_behaviors": ["view_product_12"]
}
```

**Recommend:**
```
GET http://localhost:8000/recommendations/1/?limit=10
```

**Next action:**
```
GET http://localhost:8011/api/recommender/next-action/1/
```

### HD.27 Checklist hoàn thành Chương 3 theo form yêu cầu

| Mục form | Có trong tài liệu? |
|----------|-------------------|
| 3.1 Phân tích yêu cầu | ✅ 3.1.1, 3.1.2 |
| 3.2 Kiến trúc tổng thể | ✅ Sơ đồ Mermaid + giải thích |
| 3.3 Knowledge Base | ✅ Pipeline 5 bước |
| 3.4 Vector Database | ✅ ChromaDB không có, pickle có |
| 3.5 RAG | ✅ Sequence + architecture |
| 3.6 GraphRAG | ✅ NetworkX + Neo4j |
| 3.7 Neo4j | ✅ Cypher ví dụ |
| 3.8 Deep Learning | ✅ 3.8.1–3.8.3 |
| 3.9 Thực nghiệm | ✅ 3 bảng + nhận xét |
| 3.10 Deploy | ✅ Docker diagram |
| 3.11 Chat + DL | ✅ Sequence diagram |
| 3.12 Tích hợp E-commerce | ✅ UI flows |
| 3.13 Recommender | ✅ Phần dài nhất |
| 3.14 Đánh giá | ✅ Ưu/nhược điểm |

---

*Hết Phần mở rộng 3 — Chương 3 hoàn chỉnh theo form đồ án.*
"""

def main():
    t = CH3.read_text(encoding="utf-8")
    if "## PHẦN MỞ RỘNG 3" in t:
        t = t.split("## PHẦN MỞ RỘNG 3")[0].rstrip()
    t += FINAL
    CH3.write_text(t, encoding="utf-8")
    print(f"Words: {len(re.findall(r'\w+', t))}, Lines: {len(t.splitlines())}")

if __name__ == "__main__":
    main()
