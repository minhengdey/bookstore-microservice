# -*- coding: utf-8 -*-
import re
from pathlib import Path
CH3 = Path(__file__).parent / "CHUONG3_TAI_LIEU_AI_SERVICE.md"

VOL4 = r"""

---

## PHẦN MỞ RỘNG 4 — SƠ ĐỒ & GIẢI THÍCH BỔ SUNG (HYBRID ENGINE + RAG PRODUCTION)

### MX.1 Sơ đồ Hybrid Recommendation Engine (4+ tầng)

```mermaid
flowchart TD
    subgraph INPUT["Input"]
        I1[customer_id]
        I2[limit=10]
    end

    subgraph LAYER1["Tầng 1: Matrix CF NMF"]
        A1{Engine ready?}
        A1 -->|Yes| A2[Load W, H từ factors.npz]
        A2 --> A3["scores = W[u] @ H"]
        A3 --> A4[Exclude purchased + normalize]
        A4 --> A5[weight 4.0 x behavior_bias]
        A1 -->|No| A6[Skip CF]
    end

    subgraph LAYER2["Tầng 2: Co-purchase"]
        B1[order-service recommender-orders]
        B2[Counter products in same orders]
    end

    subgraph LAYER3["Tầng 3: Behavior DB"]
        C1[BehaviorEvent aggregate]
        C2[action_weight purchase=5...]
    end

    subgraph LAYER4["Tầng 4: BiLSTM Bias"]
        D1[predict_next_action]
        D2[behavior_bias 0.75-1.25]
    end

    subgraph MERGE["Score Merge"]
        M1[score_map accumulate]
        M2[category affinity]
        M3[global popularity]
        M4[sort + top-K]
    end

    I1 --> A1 & B1 & C1 & D1
    A5 & B2 & C2 & D2 --> M1 --> M2 --> M3 --> M4
```

*Giải thích sơ đồ:* Mỗi tầng đóng góp **điểm cộng** vào `score_map`, không thay thế lẫn nhau. Nếu NMF không sẵn sàng (cold start matrix), các tầng 2–6 vẫn chạy — hệ thống **không bao giờ trả về lỗi** mà trả về fallback có ý nghĩa.

### MX.2 Giải thích chi tiết từng tầng Hybrid (dành cho người không biết ML)

**Tầng 1 — Matrix CF (NMF):** Học từ toàn bộ khách hàng: "những người giống bạn còn thích gì". Cần user đã có trong ma trận training. Weight 4.0 là cao nhất — signal collaborative mạnh nhất khi có.

**Tầng 2 — Co-purchase:** Học từ đơn hàng: "mua A thường kèm B". Không cần embedding — chỉ đếm frequency. Đặc biệt hiệu quả với phụ kiện, combo.

**Tầng 3 — Behavior scoring:** Cộng điểm trực tiếp từ hành vi của chính user trên từng product_id. Ai view nhiều lần → điểm cao dù chưa mua.

**Tầng 4 — BiLSTM bias:** Không chọn sản phẩm trực tiếp mà **điều chỉnh volume** của các tầng khác — như "tăng âm lượng" khi user sắp mua.

**Tầng 5 — Category affinity:** Gợi ý sản phẩm **mới** trong category user thích — giải quyết long-tail trong category quen thuộc.

**Tầng 6 — Popularity:** Đảm bảo danh sách không rỗng và có sản phẩm "an toàn" cho merchant.

### MX.3 RAG Chatbot Production Flow — 6 bước giải thích

**Bước 1 — Nhận message:** Widget gửi JSON qua gateway — không gọi thẳng Groq từ browser (bảo mật API key + tránh CORS phức tạp).

**Bước 2 — Gợi ý sản phẩm:** `recommend_with_prediction()` chạy **song song** với search — chat vừa trả lời câu hỏi vừa có list sản phẩm để render card.

**Bước 3 — Fetch live catalog:** `_fetch_live_products()` đảm bảo tên/giá/stock đúng thời điểm chat — không dùng cache cũ từ CSV.

**Bước 4 — Ghép context:** Chuỗi `context_text` là "tài liệu tham khảo" bắt buộc cho LLM — càng chi tiết, càng ít hallucination.

**Bước 5 — Groq API:** `llama-3.1-8b-instant` trên Groq LPU — latency thấp phù hợp chat. Timeout 20s — widget hiển thị typing indicator.

**Bước 6 — Response:** Frontend nhận `answer` (markdown) + `products` (JSON) — có thể render rich UI.

### MX.4 Groq Integration — code và lý do

```python
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

def call_groq(system_prompt, user_message, history=None, max_tokens=512):
    messages = [{"role": "system", "content": system_prompt}]
    # append history up to 10 turns
    messages.append({"role": "user", "content": user_message})
    # urllib POST with Bearer GROQ_API_KEY
```

**Tại sao không dùng OpenAI GPT-4 trong đồ án?** Chi phí và latency cao hơn cho use case chat tư vấn SKU đơn giản. Groq đủ tốt khi có RAG context chất lượng.

**groq SDK trong requirements:** Không dùng — code dùng `urllib.request` thuần để giảm dependency conflict.

### MX.5 Tích hợp E-commerce — các màn hình

| Màn hình | File template/JS | Chức năng AI |
|----------|------------------|--------------|
| Base layout | `base.html` | Load chatbot widget |
| Trang chủ | `home.html`, `home-storefront.js` | Carousel gợi ý |
| Chi tiết SP | `product_detail.html` | Behavior tracking |
| Admin recommend | `admin_views.py` | MLOps panel |

**Seller portal AI:** Không tìm thấy trong source code dự án.

### MX.6 Behavior tracking — `gateway/behavior_tracking.py`

Gateway nhận event từ JS, gắn `customer_id` từ session, forward tới recommender `POST /api/recommender/events/`. Đây là **vòng phản hồi** khiến AI "học" hành vi mới mỗi phiên đăng nhập.

### MX.7 Implicit ALS naming vs NMF implementation

Tên biến môi trường `IMPLICIT_CF_ALS_WEIGHT` dùng từ giai đoạn thiết kế ban đầu (ALS = Alternating Least Squares). Code thực tế `train_implicit_cf_local` dùng **sklearn NMF** (Non-negative Matrix Factorization). Cả hai đều là matrix factorization — documentation dùng thuật ngữ "Matrix CF (NMF)" cho chính xác.

### MX.8 Đọc file `model_best_evaluation.txt` — hướng dẫn

File nằm tại `recommender-ai-service/models/model_best_evaluation.txt`. Admin API `_parse_evaluation_file()` đọc file này hiển thị dashboard. Nội dung gồm:
- Bảng so sánh GRU/LSTM/BiLSTM
- Lý do chọn BiLSTM (bullet list)
- F1 per class
- So sánh v4→v5 cải tiến

Đây là **bằng chứng thực nghiệm** khi bảo vệ — không cần chạy lại training.

### MX.9 Plots trong thư mục `plots/`

| File | Dùng cho mục |
|------|--------------|
| training_curves.png | 3.9 thực nghiệm |
| model_comparison.png | 3.8.2 so sánh |
| confusion_matrix_best.png | 3.9 phân tích lỗi |
| f1_per_class.png | 3.9.1 bảng F1 |
| v6_model_comparison.png | BS.10 tham khảo v6 |

### MX.10 Kiến thức nền — Embedding là gì? (giải thích không công thức)

Hãy tưởng tượng mỗi sản phẩm được gán một "tọa độ" trong không gian nhiều chiều. Sản phẩm gần nhau trong không gian này có nghĩa tương tự — ví dụ hai loại son môi khác brand nhưng cùng mô tả "son lì màu đỏ" sẽ có tọa độ gần nhau. Câu hỏi của khách cũng được chuyển thành tọa độ — hệ thống tìm sản phẩm có tọa độ gần nhất.

### MX.11 Kiến thức nền — Collaborative Filtering là gì?

Nếu User A và User B đều mua sách Python và sách Java, hệ thống suy ra A và B có sở thích giống nhau. Khi B mua thêm sách Go, gợi ý sách Go cho A — dù A chưa từng tìm kiếm Go. Đây là **lọc cộng tác** — không cần đọc mô tả sách, chỉ cần ma trận ai mua gì.

### MX.12 Kiến thức nền — BiLSTM là gì?

LSTM (Long Short-Term Memory) là mạng neural có "bộ nhớ" cho chuỗi dài. BiLSTM chạy LSTM xuôi và ngược trên cùng chuỗi hành vi — như đọc nhật ký mua sắm từ đầu tới cuối và từ cuối về đầu để hiểu ngữ cảnh đầy đủ.

### MX.13 Kiến thức nền — RAG vs Search engine

Search engine truyền thống (TF-IDF) tìm từ khóa khớp. RAG = Search + LLM viết lại kết quả thành câu tư vấn tự nhiên. Khách không cần đọc list 10 link — Mochi tóm tắt và giải thích.

### MX.14 Failure modes và cách hệ thống xử lý

| Failure | Xử lý trong code |
|---------|------------------|
| Groq 429/500 | Retry gateway + fallback message |
| product-service timeout | Skip product hydrate, partial answer |
| Neo4j down | Log error, CF pipeline vẫn chạy PG |
| Empty catalog index | rebuild_index on startup |
| BiLSTM load fail | behavior_bias=1.0, hybrid vẫn chạy |
| User không trong NMF | Skip CF tầng, dùng behavior+category |

Thiết kế **degradation graceful** — không có single point of failure cho UX chính.

### MX.15 Bảo mật dữ liệu hành vi

BehaviorEvent chứa customer_id và product_id — dữ liệu nhạy cảm. Nằm trong `recommender_db` nội bộ docker network, không expose ra internet. API ghi event qua gateway đã xác thực session.

### MX.16 So sánh độ phức tạp các module (LOC ước lượng)

| Module | Độ phức tạp | Lý do |
|--------|-------------|-------|
| recommender_service.py | Cao | 6 tầng scoring |
| rag_llm.py | Cao | Orchestration |
| hybrid_retriever.py | Trung bình | ML sklearn + ST |
| inference_utils.py | Trung bình | TF load + predict |
| intent_router.py | Thấp | Rule regex |
| event_handler.py | Trung bình | Multi-store write |

### MX.17 Kịch bản test manual đầy đủ (15 phút)

1. `docker-compose up` — đợi recommender entrypoint xong (index built).
2. Đăng ký user mới → gợi ý `random-cold-start`.
3. Xem 5 sản phẩm category beauty → refresh → beauty xuất hiện nhiều hơn.
4. Thêm 1 sản phẩm vào giỏ (nếu flow hoàn chỉnh) → next-action có thể `purchase`.
5. Mở chat: "xin chào" → GREETING.
6. "tìm kem dưỡng" → SEARCH + products list.
7. "gợi ý thêm" → RECOMMEND + hybrid.
8. "chính sách đổi trả" → POLICY không bịa giá.
9. Check Neo4j browser `localhost:7474` — thấy nodes sau events.
10. Check logs recommender — strategy string trong RecommendationLog.

### MX.18 Tài liệu tham khảo kỹ thuật (đọc thêm)

- RAG: Lewis et al., Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks
- NMF collaborative filtering: Koren et al., Matrix Factorization Techniques
- BiLSTM: Graves & Schmidhuber, Framewise phoneme classification
- Graph-based CF: Neo4j developer docs — Cypher pattern matching
- Sentence-BERT: Reimers & Gurevych, sentence-transformers

### MX.19 Lịch sử phiên bản AI trong dự án (timeline)

| Giai đoạn | Mốc | Kết quả |
|-----------|-----|---------|
| v3 data | Entropy cao | Acc ~28% |
| v4 data fix | Session goals | Acc ~52-65% |
| v5 architecture | BiLSTM+Attn | Acc 77.3% deploy |
| v6 compare | 7 models | DIN leakage, không deploy |
| Production | RAG Mochi + hybrid 6 tầng | E2E demo |

### MX.20 Kết luận Phần mở rộng 4

Phần này bổ sung sơ đồ hybrid engine, giải thích nền tảng cho người mới, failure modes, và kịch bản test — đảm bảo Chương 3 đủ chiều sâu **giảng dạy** lẫn **kỹ thuật**, phục vụ bảo vệ đồ án trước hội đồng.

---

*Chương 3 — Thiết kế và Triển khai AI-Service — Hết.*
"""

def main():
    t = CH3.read_text(encoding="utf-8")
    if "MX.20 Kết luận Phần mở rộng 4" in t:
        t = t.split("## PHẦN MỞ RỘNG 4")[0].rstrip()
    if "## PHẦN MỞ RỘNG 4" not in t:
        t += VOL4
    else:
        t += VOL4
    CH3.write_text(t, encoding="utf-8")
    print(f"Words: {len(re.findall(r'\w+', t))}")

if __name__ == "__main__":
    main()
