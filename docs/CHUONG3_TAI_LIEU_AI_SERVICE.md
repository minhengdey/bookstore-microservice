# CHƯƠNG 3: AI SERVICE CHO TƯ VẤN SẢN PHẨM

Sự phát triển của một hệ thống E-commerce hiện đại không chỉ dừng lại ở việc đáp ứng nhanh các giao dịch mua bán, mà còn nằm ở khả năng thấu hiểu và định hướng hành vi tiêu dùng của khách hàng. Chương này tập trung vào thiết kế và triển khai AI Service – một microservice độc lập đóng vai trò như bộ não phân tích dữ liệu hành vi (Behavioral Analytics) kết hợp với Trí tuệ nhân tạo Sinh tạo (Generative AI) để đem đến những gợi ý cá nhân hóa và tự động hóa khâu chăm sóc khách hàng.

## 3.1 Mục tiêu
Xây dựng một hệ thống AI gợi ý sản phẩm đa chiều dựa trên các nguyên lý cốt lõi:
- Phân tích và dự đoán dựa trên Chuỗi hành vi người dùng theo thời gian thực (click, search, add-to-cart, purchase...).
- Rút trích Quan hệ ngữ nghĩa của sản phẩm thông qua Đồ thị tri thức (Knowledge Graph - Neo4j).
- Tích hợp Ngữ cảnh truy vấn thông minh qua Chatbot (Sử dụng kiến trúc RAG để hạn chế "ảo giác" của Mô hình Ngôn ngữ Lớn).

Sản phẩm đầu ra kỳ vọng của Microservice này bao gồm:
- Danh sách sản phẩm đề xuất (Recommendation List) mang tính cá nhân hóa cao cho mỗi người dùng truy cập.
- Một Chatbot tư vấn tự động, hiểu rõ lịch sử mua hàng và có thể giải đáp chi tiết về các sản phẩm liên quan.

## 3.2 Kiến trúc AI Service
Khác với các dịch vụ kinh doanh cốt lõi (như Order hay Payment), AI Service được cô lập hoàn toàn thành một thực thể độc lập nhằm chịu tải các tác vụ xử lý ma trận và suy luận Machine Learning cực nặng.
- **Input:** Khai thác dữ liệu hành vi chuỗi (user behavior) được đẩy từ API Gateway và các log truy vấn của người dùng.
- **Processing Engine:**
  - Sequence Modeling sử dụng mạng Nơ-ron hồi quy hai chiều (BiLSTM) tích hợp cơ chế Chú ý (Attention Mechanism).
  - Knowledge Graph sử dụng CSDL đồ thị Neo4j.
  - Retrieval-Augmented Generation (RAG) kết nối trực tiếp với LLM thông qua API hoặc Local Models.
- **Output:** Dữ liệu dự đoán (`recommendation list`) và phản hồi văn bản (`chatbot response`) được trả về cho Frontend qua API nội bộ.

## 3.3 Thu thập dữ liệu
Khâu cốt lõi của mọi mô hình AI là Dữ liệu. Trong dự án này, dữ liệu không tĩnh mà mang tính thời gian thực.

### 3.3.1 Dữ liệu Hành vi Người dùng (User Behavior Data)
Hệ thống AI xử lý dữ liệu hành vi dạng chuỗi thời gian (Time-series data). Mỗi thao tác của khách hàng trên giao diện web như: `view` (xem chi tiết), `click` (bấm vào ảnh), `add_to_cart` (thêm vào giỏ), `purchase` (thanh toán hoàn tất), `wishlist` (yêu thích), `search` (tìm kiếm), `review` (đánh giá) đều được ghi nhận lại với độ phân giải tính theo mili-giây.

### 3.3.2 Ví dụ và Cấu trúc Dataset
Dự án sử dụng cơ chế giả lập dữ liệu (Simulation) để sinh ra hàng trăm ngàn bản ghi dưới dạng file CSV/DB nhằm phục vụ huấn luyện (tại `recommender-ai-service/app/management/commands/seed_behaviors.py`). 
Mỗi bản ghi được định dạng rõ ràng bao gồm: `user_id`, `session_id`, `product_id`, `action`, `timestamp`, `device`. Cấu trúc này cho phép mô hình nhìn thấu được chuỗi hành động dẫn đến quyết định mua hàng cuối cùng.

## 3.4 Mô hình Sequence Modeling (BiLSTM Attention)

### 3.4.1 Ý tưởng cốt lõi
Mọi tương tác của người dùng trên web không phải là các sự kiện ngẫu nhiên rời rạc, mà là một chuỗi tuần tự theo thời gian tuân theo các chuỗi quy luật tiềm ẩn. Mạng BiLSTM (Bidirectional Long Short-Term Memory) sẽ quan sát chuỗi hành động này từ quá khứ đến hiện tại để nhận diện ý định thực sự của người dùng. Kỹ thuật Multi-Head Attention giúp mô hình "tập trung" vào các hành động mang tính quyết định (ví dụ việc add-to-cart thường có trọng số lớn hơn việc click thông thường).

### 3.4.2 Cấu trúc Model chi tiết
Kiến trúc AI được viết bằng TensorFlow/Keras, tối ưu hóa qua các lớp LayerNormalization và Residual Connection để triệt tiêu hiện tượng vanishing gradient.

Trích xuất đoạn mã cấu trúc BiLSTM Attention từ `train_models.py` của dự án:
```python
def build_bilstm_attention_model(in_shape, NUM_CLASSES):
    inp = layers.Input(shape=in_shape)
    
    # Chuẩn hóa dữ liệu đầu vào
    x   = layers.LayerNormalization()(inp)   
    
    # Lớp BiLSTM thứ nhất: Bắt các phụ thuộc chuỗi theo cả hai chiều
    x   = layers.Bidirectional(layers.LSTM(256, return_sequences=True))(x)
    x   = layers.LayerNormalization()(x)
    x   = layers.Dropout(0.30)(x) # Chống overfitting (Regularization)
    
    # Lớp BiLSTM thứ hai
    x   = layers.Bidirectional(layers.LSTM(128, return_sequences=True))(x)
    
    # Cơ chế Tự Chú Ý (Self-Attention) phân tích tầm quan trọng của các hành vi
    attn = MultiHeadSelfAttention(256, num_heads=4)(x)
    
    # Residual connection
    x    = layers.Add()([x, attn]) 
    x    = layers.LayerNormalization()(x)
    
    # Global Pooling thay cho Flatten để giảm số lượng tham số
    x    = layers.GlobalAveragePooling1D()(x)
    
    # Các lớp mạng nơ-ron dày đặc (Dense layers)
    x    = layers.Dense(256, activation="gelu")(x) 
    x    = layers.Dropout(0.25)(x)
    x    = layers.Dense(128, activation="gelu")(x)
    x    = layers.Dropout(0.15)(x)
    
    # Lớp đầu ra Classification
    out  = layers.Dense(NUM_CLASSES, activation="softmax", dtype="float32")(x)
    
    m    = Model(inp, out, name="BiLSTM_Attention")
    return m
```

### 3.4.3 Quá trình Huấn luyện (Training) và Tối ưu hóa
Quá trình Training sử dụng bộ lập lịch học thay đổi linh hoạt (Warmup Cosine Decay) để mô hình hội tụ tốt hơn và tránh việc chệch hướng ở các epoch đầu.

Đoạn mã cấu trúc Scheduler (từ dự án):
```python
class WarmupCosineDecay(Callback):
    def __init__(self, warmup_epochs=3, total_epochs=20, min_lr=1e-5, peak_lr=1e-3):
        super().__init__()
        self.warmup_epochs = warmup_epochs
        self.total_epochs = total_epochs
        self.min_lr = min_lr
        self.peak_lr = peak_lr

    def on_epoch_begin(self, epoch, logs=None):
        if epoch < self.warmup_epochs:
            lr = self.min_lr + (self.peak_lr - self.min_lr) * epoch / max(self.warmup_epochs - 1, 1)
        else:
            progress = (epoch - self.warmup_epochs) / max(self.total_epochs - self.warmup_epochs, 1)
            lr = self.min_lr + 0.5 * (self.peak_lr - self.min_lr) * (1 + math.cos(math.pi * progress))
            
        tf.keras.backend.set_value(self.model.optimizer.lr, lr)
```

## 3.5 Đồ thị Tri thức với Neo4j (Knowledge Graph)

### 3.5.1 Mô hình đồ thị
CSDL quan hệ (SQL) rất kém trong việc lướt qua nhiều lớp dữ liệu chồng chéo (ví dụ: Tìm "Khách hàng A" mua "Sản phẩm B", sản phẩm B lại thường được mua cùng "Sản phẩm C" bởi "Khách hàng D"). Neo4j sinh ra để giải quyết bài toán này. Hệ thống ánh xạ các tương tác mua bán thành các nút (Nodes: `User`, `Product`, `Category`) và cạnh (Edges: `PERFORMED`, `BELONGS_TO`).

### 3.5.2 Xây dựng đồ thị (Cypher & NetworkX)
Việc nhồi hàng vạn dữ liệu vào Neo4j được hệ thống hóa qua Python sử dụng thư viện đồ thị. 

Mã nguồn sinh Graph (từ logic nội bộ của AI Service):
```python
import networkx as nx

def build_knowledge_graph(df):
    G = nx.MultiDiGraph()
    
    # 1. Khởi tạo Nút định danh người dùng
    for uid in df["user_id"].unique():
        G.add_node(uid, label="User")

    # 2. Tạo Liên kết (Edges) thể hiện Ngữ nghĩa Bán lẻ
    for _, row in df.iterrows():
        # Khách hàng A -> [Hành động] -> Sản phẩm B
        G.add_edge(
            row["user_id"], 
            row["product_id"],
            relation="PERFORMED",
            action=row["action"]
        )
        
        # Sản phẩm B -> [Thuộc Về] -> Danh mục
        G.add_edge(
            row["product_id"], 
            row["category"],
            relation="BELONGS_TO"
        )
    return G
```

### 3.5.3 Truy vấn gợi ý đồ thị (Collaborative Filtering)
Neo4j Graph hỗ trợ truy vấn các hành vi của những khách hàng tương đồng cực nhanh. Bằng thuật toán Cypher, hệ thống lập tức tìm ra cụm sản phẩm liên đới theo hành vi số đông, bổ khuyết cho mô hình BiLSTM phân tích cá nhân.

## 3.6 Hệ thống RAG (Retrieval-Augmented Generation)

### 3.6.1 Cơ chế LLM và Bổ sung Ngữ cảnh
Để hệ thống Chatbot tư vấn không sinh ra những câu trả lời "ảo giác" (hallucination) hay tư vấn một sản phẩm E-commerce của một công ty khác, nền tảng tích hợp cơ chế RAG. Mọi câu hỏi của người dùng đều sẽ được chèn thêm bối cảnh (Context) – chính là lịch sử mua hàng cá nhân và gợi ý từ mô hình BiLSTM – trước khi được đẩy tới Mô hình Ngôn ngữ Lớn (LLM).

### 3.6.2 Trích xuất mã nguồn RAG Chatbot
Dưới đây là mã nguồn lõi xử lý luồng hội thoại kết hợp AI, trích từ `rag_llm.py` của hệ thống:

```python
class RAGChatLLM:
    def _build_context(self, user_id: str) -> dict:
        """Thu thập bối cảnh cá nhân hóa trước khi sinh phản hồi."""
        # 1. Trích xuất Lịch sử thao tác
        history  = self.rag.retrieve_user_history(user_id, top_k=8)
        
        # 2. Yêu cầu BiLSTM dự đoán nhu cầu tiếp theo
        recs     = self.rag.recommend_products(user_id) 
        
        # 3. Quét đồ thị Neo4j tìm User tương đồng
        similar  = self.rag.retrieve_similar_users(user_id, top_k=3)
        
        return {
            "user_id": user_id,
            "history": history,
            "recommendations": recs.get("recommendations", [])[:6]
        }
        
    def _fallback(self, message: str, ctx: dict) -> str:
        """Cơ chế dự phòng khi API LLM hết hạn ngạch hoặc mạng bị đứt gãy."""
        if any(k in message.lower() for k in ["gợi ý", "recommend", "tư vấn"]):
            recs_text = ", ".join(ctx["recommendations"])
            return f"Dựa trên lịch sử duyệt web của bạn, hệ thống thông minh của chúng tôi gợi ý các sản phẩm: {recs_text}"
        return "Xin chào, hệ thống hỗ trợ ngôn ngữ tự nhiên hiện đang bảo trì. Vui lòng thử lại sau ít phút."
```

## 3.7 Đánh giá Thực nghiệm Mô hình AI

### 3.7.1 Mục tiêu đánh giá
Kiểm chứng độ chính xác (Accuracy), độ đo F1 (F1-score) của cấu trúc BiLSTM tích hợp Attention trong việc tiên đoán hành vi giỏ hàng; và kiểm tra tính năng giảm thiểu ảo giác của mô hình RAG tích hợp Neo4j.

### 3.7.2 Kết quả thực nghiệm
Với bộ dữ liệu hành vi lớn của hệ thống, mạng BiLSTM kết hợp Cơ chế chú ý (Attention Mechanism) đã học thành công các chuỗi hành vi mua sắm phức tạp, đạt được khả năng phân lớp cực kỳ ấn tượng khi đánh giá độ tương thích của các sản phẩm đề xuất. Bảng kết quả huấn luyện (Training Logs) luôn thể hiện Loss giảm tiệm cận cực đại ở các Epoch cuối.
Sự kết hợp giữa sức mạnh AI Phân tích (Analytics AI - BiLSTM) và AI Sinh tạo (Generative AI - RAG Chatbot) đã biến hệ thống E-commerce này thành một nền tảng bán lẻ thông minh vượt trội so với các hệ thống truyền thống chỉ dựa trên truy vấn CSDL tĩnh.
