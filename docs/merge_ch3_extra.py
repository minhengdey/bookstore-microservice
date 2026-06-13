# -*- coding: utf-8 -*-
"""Merge legacy detailed technical content into Chapter 3."""
import re
from pathlib import Path

ROOT = Path(__file__).parent
CH3 = ROOT / "CHUONG3_TAI_LIEU_AI_SERVICE.md"
OLD = Path(r"C:\Users\dlmin\.cursor\projects\d-Study-Nam4-Ky2-KTVHTPM-ai-ktmp-e-commerce\uploads\d__Study_Nam4_Ky2_KTVHTPM_ai-ktmp_e-commerce_docs_CHUONG3_TAI_LIEU_AI_SERVICE-L1-L1396-0.md")

EXTRA = r"""

---

## PHẦN BỔ SUNG CHI TIẾT KỸ THUẬT (đối chiếu artifact & tài liệu phát triển)

> **Lưu ý quan trọng:** Các mục dưới đây mô tả pipeline training BiLSTM v5/v6 và so sánh mô hình dựa trên `models/model_best_evaluation.txt`, plots trong `plots/`, và nhật ký phát triển. Script `train_models_v5.py`, `train_models_v6.py`, `data/generate_data_v4.py` — **Không tìm thấy trong source code dự án** tại thời điểm đối chiếu repository; artifact `model_best.keras` và `encoders.pkl` **có sẵn** và được load bởi `inference_utils.py`.

### BS.1 Pipeline dữ liệu Training BiLSTM (mô tả quy trình đã dùng để tạo artifact)

```mermaid
flowchart LR
    subgraph DATA_SRC["Nguồn dữ liệu"]
        D1[data_user500.csv]
        D2[Retailrocket — script convert]
        D3[Online Retail UCI — script convert]
    end

    subgraph PREPROCESS["Tiền xử lý"]
        P1[LabelEncoder]
        P2[Feature Engineering 18 dims]
        P3[Sliding Window SEQ_LEN=20]
        P4[Oversampling rare ×4]
        P5[Cache seq .npz]
    end

    subgraph SPLIT["Chia tập"]
        S1[70% Train]
        S2[15% Val]
        S3[15% Test]
    end

    subgraph TRAIN["Huấn luyện"]
        T1[GRU]
        T2[LSTM]
        T3[BiLSTM + Attention]
    end

    subgraph EVAL["Đánh giá"]
        E1[Accuracy F1 Confusion Matrix]
        E2[model_best.keras]
    end

    D1 --> P1 --> P2 --> P3 --> P4 --> P5
    P5 --> S1 & S2 & S3
    S1 --> T1 & T2 & T3
    S3 --> E1 --> E2
```

**Giải thích từng bước cho người đọc chưa biết AI:**

1. **Thu thập dữ liệu:** Mỗi dòng CSV là một hành động của user trên sàn (xem, click, mua...). Đây là "nhật ký hành vi" mà model sẽ học.

2. **LabelEncoder:** Chuyển chữ (ví dụ `fashion`) thành số để neural network xử lý được.

3. **Sliding window:** Nếu user có 50 hành động, cắt thành nhiều đoạn 20 hành động liên tiếp — mỗi đoạn dự đoán hành động thứ 21. Tăng số mẫu training.

4. **Oversampling:** Hành động hiếm (`review`) được nhân bản để model không bỏ qua.

5. **Train/Val/Test:** Train để học, Val để điều chỉnh learning rate, Test để báo cáo metric cuối — **không** dùng test để chọn model (tránh leakage).

6. **Chọn BiLSTM:** So sánh 3 kiến trúc, chọn accuracy cao nhất, copy vào `models/model_best.keras`.

### BS.2 Transition Entropy — bài học phát triển dữ liệu

Entropy chuyển trạng thái đo "độ hỗn loạn" của hành vi: nếu user nhảy ngẫu nhiên giữa các action, ceiling accuracy lý thuyết thấp.

| Phiên bản data | Entropy | Ceiling lý thuyết | Accuracy thực tế |
|----------------|---------|-------------------|------------------|
| v3 | 2.54/3.0 | ~33.8% | ~28% |
| v4+ | 2.05/3.0 | ~56.2% | 52–77% |

**Insight:** Trước khi tăng độ phức tạp model, phải đảm bảo dữ liệu có pattern học được. Đây là nguyên tắc "garbage in, garbage out" — rác vào thì AI không cứu được.

**Transition matrix ví dụ (v4+):** `search→view` 70%, `view→click` 55%, `add_to_cart→purchase` 65% — phản ánh funnel mua hàng thực tế.

### BS.3 Session Goals — nhãn ngữ cảnh session

| Goal | Chuỗi hành vi điển hình | Mục đích |
|------|-------------------------|----------|
| buying | search→view→click→cart→purchase | Mua nhanh |
| browsing | search→view→view→click | Dạo xem |
| abandoning | ...→cart→remove→search | Bỏ giỏ |
| comparing | view→wishlist→view→wishlist | So sánh |
| reviewing | purchase→review→search | Sau mua |

Feature `goal_code` trong vector 18 chiều giúp BiLSTM biết "session này đang theo kịch bản nào".

### BS.4 Kiến trúc BiLSTM đầy đủ (training spec — khớp inference layer)

```
Input (20, 18)
  → LayerNormalization
  → Bidirectional LSTM(256) → 512 dims
  → LayerNorm + Dropout(0.30)
  → Bidirectional LSTM(128) → 256 dims
  → MultiHeadSelfAttention(256, 4 heads)
  → Residual Add + LayerNorm
  → GlobalAveragePooling1D
  → Dense(256, GELU) + Dropout(0.25)
  → Dense(128, GELU) + Dropout(0.15)
  → Dense(8, softmax)
```

**Tham số:** ~2.8M parameters.

**Tại sao LayerNorm trước LSTM (không phải BatchNorm sau)?** BatchNorm phụ thuộc batch — khó với sequence nhỏ. LayerNorm chuẩn hóa từng timestep độc lập — ổn định gradient cho RNN.

### BS.5 Loss function — Label Smoothing + Class Weights

Thay vì ép model predict 100% một class, label smoothing dạy "90% purchase, 10% phân tán các class khác" — giảm overconfidence.

Class weights tăng penalty khi model bỏ sót class hiếm (`review`, `wishlist`).

**Công thức trực giác:** Loss = CrossEntropy(smoothed_label, prediction) × weight[class].

### BS.6 Learning Rate Schedule

| Giai đoạn | LR | Mục đích |
|-----------|-----|----------|
| Epoch 0–4 | 1e-5 → 3e-4 linear | Warmup — tránh gradient nổ |
| Epoch 5+ | ReduceLROnPlateau | Giảm LR khi val_loss plateau |
| Cuối | Cosine decay → 0 | Fine-tune nhẹ |

### BS.7 Hyperparameter Search (kết quả tham khảo)

| Model | Batch | LR | Accuracy | F1-macro |
|-------|-------|-----|----------|----------|
| BiLSTM | 256 | 3e-4 | 0.5223 | 0.5032 |
| BiLSTM | 512 | 3e-4 | 0.4961 | 0.4831 |
| GRU | 256 | 3e-4 | 0.3808 | 0.3716 |

Chọn `batch=256`, `peak_lr=3e-4` cho full training 45 epochs.

### BS.8 Bảng so sánh 3 mô hình v5 (metric đầy đủ)

| Model | Accuracy | F1-macro | F1-weighted | Epochs | Thời gian (s) |
|-------|----------|----------|-------------|--------|---------------|
| GRU | 0.6274 | 0.6018 | 0.6203 | 45 | ~12000 |
| LSTM | 0.6930 | 0.6826 | 0.6927 | 45 | ~18000 |
| **BiLSTM** | **0.7730** | **0.7598** | **0.7703** | **45** | **39602** |

### BS.9 F1 theo class — BiLSTM production model

| Action | F1 | Đánh giá |
|--------|-----|----------|
| remove_from_cart | 0.899 | Rất tốt |
| view | 0.832 | Tốt |
| wishlist | 0.815 | Tốt |
| review | 0.819 | Tốt |
| search | 0.730 | Khá |
| add_to_cart | ~0.65 | TB |
| click | ~0.60 | TB |
| purchase | ~0.55 | Cần cải thiện — do nhiễu ngoài session |

**Liên hệ hệ thống:** Dù `purchase` F1 thấp hơn, `behavior_bias` vẫn hữu ích khi confidence > 0.6 — hybrid recommender không chỉ dựa vào DL.

### BS.10 Thí nghiệm v6 — 7 kiến trúc (không deploy)

| Model | Accuracy | Ghi chú |
|-------|----------|---------|
| DIN | 1.0000 | **Loại** — data leakage |
| GRU4Rec | 0.6355 | Embedding-only |
| BiLSTM_Attn v6 | 0.6351 | Không có 18 features |
| SASRec | 0.6342 | Transformer session |
| BERT4Rec | 0.6342 | Masked prediction |
| NCF | 0.5621 | Cold start yếu |
| LightGCN | 0.3209 | Graph chưa đủ |

**Kết luận:** v5 feature-engineered > v6 embedding-only. DIN không dùng production.

### BS.11 Biểu đồ thực nghiệm (files trong repo)

| File | Nội dung |
|------|----------|
| `plots/training_curves.png` | Train/Val loss & accuracy 3 model v5 |
| `plots/model_comparison.png` | Bar chart Acc/F1 |
| `plots/confusion_matrix_best.png` | Ma trận nhầm lẫn BiLSTM |
| `plots/f1_per_class.png` | F1 từng action |
| `plots/v6_model_comparison.png` | So sánh 7 model v6 |

### BS.12 Ma trận nhầm lẫn — cách đọc

Confusion matrix hàng = nhãn thật, cột = nhãn dự đoán. Đường chéo cao = tốt. Nhầm `click`↔`view` là bình thường — hai hành động gần nhau trên funnel.

### BS.13 RAG Chat — luồng `_resolve_products_for_intent` chi tiết

| Intent | Nguồn sản phẩm ưu tiên | Fallback |
|--------|------------------------|----------|
| SEARCH | hybrid_search + keyword catalog | RAGSystem |
| RECOMMEND | RecommenderService | popular category |
| POLICY | Không gợi ý sản phẩm | policy text |
| GREETING | Hot products | empty |
| FOLLOW_UP | history + price filter | hybrid |

### BS.14 `ProductReranker` — Cross-Encoder

Model: `cross-encoder/mmarco-mMiniLMv2-L384-v1` — nhận cặp (query, product_doc) trả relevance score. Chạy trên top-20 sau RRF, xuất top-5.

Fallback feature-based: cộng điểm nếu khớp category keyword, brand, stock>0.

### BS.15 `consume_events` — RabbitMQ routing

Consumer đăng ký queue và dispatch:
- `catalog.product.created/updated` → `handle_catalog_event`
- `interaction.*` → `handle_interaction_event`
- `payment.succeeded` → `handle_payment_event`
- `user.created/updated` → `handle_user_event`

Đảm bảo Knowledge Base và graph **không stale** so với microservice nguồn.

### BS.16 Admin API MLOps (`admin_api.py`)

| Endpoint | Chức năng |
|----------|-----------|
| GET models | Liệt kê ModelVersion |
| POST retrain | Trigger `train_implicit_cf_local` |
| POST activate | Đổi model ACTIVE |
| GET evaluation | Parse `model_best_evaluation.txt` |

**Retrain BiLSTM từ admin:** Không tìm thấy — chỉ NMF CF.

### BS.17 Cold Start AI — chiến lược đa tầng

| Tầng | Cơ chế | Code |
|------|--------|------|
| 1 | Random catalog shuffle | `random-cold-start` |
| 2 | Global popularity | `get_global_popularity_scores` |
| 3 | Category từ session (chat) | `retrieve_popular_in_category` |
| 4 | Trending Redis | `get_trending_ids` |

### BS.18 Bảo mật AI endpoints

- `chat-ktmp` public qua gateway — không lộ Groq key.
- Internal APIs dùng `common/auth.py` HMAC nếu gọi service-to-service.
- `BehaviorEventView` nhận event từ gateway đã authenticate user session.

### BS.19 Performance tuning khuyến nghị

| Bottleneck | Giải pháp |
|------------|-----------|
| Embedding load chậm | AIModelSingleton + preload entrypoint |
| Groq timeout | Retry gateway 3×, fallback local |
| Neo4j MERGE chậm | Batch write (chưa có — ghi nhận hướng cải thiện) |
| Catalog index stale | Cron `build_catalog_index --force` |

### BS.20 Tổng kết luồng dữ liệu AI toàn hệ thống (one-page)

```
[User UI]
   ├─(view/click)──► behavior_tracking ──► BehaviorEvent ──┬─► BiLSTM ──► behavior_bias
   │                                                      ├─► NMF CF (periodic train)
   │                                                      ├─► Neo4j MERGE
   │                                                      └─► Redis sequence
   ├─(chat)───────► /ai/chat/ ──► RAGChatLLM ──┬─► HybridRetriever (pickle index)
   │                                           ├─► RecommenderService
   │                                           ├─► RAGSystem (NetworkX)
   │                                           └─► Groq LLM ──► answer
   └─(home)───────► /recommendations/ ──► RecommenderService ──► Top-N products
```

**Đây là câu trả lời cho "AI hoạt động như thế nào trong hệ thống":** Mọi đường dẫn đều bắt đầu từ hành vi hoặc câu hỏi người dùng, đi qua retrieval/reasoning có kiểm chứng dữ liệu nội bộ, kết thúc bằng gợi ý sản phẩm hoặc câu trả lời có link — **không hallucinate SKU**.

"""

def main():
    base = CH3.read_text(encoding="utf-8")
    # Remove duplicate ending if re-run
    marker = "## PHẦN BỔ SUNG CHI TIẾT KỸ THUẬT"
    if marker in base:
        base = base.split(marker)[0].rstrip()
    # Remove old appendix duplicate
    if "## PHỤ LỤC CHƯƠNG 3" in base and marker not in base:
        pass
    merged = base + EXTRA
    CH3.write_text(merged, encoding="utf-8")
    words = len(re.findall(r"\w+", merged))
    print(f"Merged -> {words} words, {len(merged.splitlines())} lines")

if __name__ == "__main__":
    main()
