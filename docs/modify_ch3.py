import os
import re

fpath = r'd:\Study\Nam4_Ky2\KTVHTPM\ai-ktmp\bookstore-microservice\docs\CHUONG3_TAI_LIEU_AI_SERVICE.md'
if os.path.exists(fpath):
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    replacements = [
        (r'`recommender-ai-service/app/services/implicit_cf_engine\.py`', 'lớp xử lý tính toán Lọc cộng tác (Implicit CF Engine)'),
        (r'`recommender-ai-service/app/services/recommender_service\.py`', 'lớp Điều phối Dịch vụ Gợi ý (Recommender Service)'),
        (r'`recommender-ai-service/app/services/behavior_prediction_service\.py`', 'lớp Dịch vụ Dự đoán Hành vi (Behavior Prediction Service)'),
        (r'`recommender-ai-service/app/services/behavior_actions\.py`', 'tập hợp các quy tắc định chuẩn hành vi người dùng'),
        (r'`recommender-ai-service/rag/rag_llm\.py`', 'module tích hợp Mô hình Ngôn ngữ lớn (RAG LLM)'),
        (r'`recommender-ai-service/rag/retriever\.py`', 'module truy xuất thông tin (Retriever)'),
        (r'`recommender-ai-service/knowledge_base/build_kb_graph_v3\.py`', 'kịch bản xây dựng cơ sở tri thức đồ thị'),
        (r'`recommender-ai-service/models/train_models_v5\.py`', 'kịch bản huấn luyện mô hình học sâu'),
        (r'`recommender-ai-service/train_implicit_cf\.py`', 'kịch bản huấn luyện mô hình Lọc cộng tác'),
        (r'`recommender-ai-service/data/generate_data_v4\.py`', 'kịch bản sinh dữ liệu tổng hợp (Synthetic Data Generator)'),
        (r'`recommender-ai-service/app/views/recommender_views\.py`', 'lớp giao diện lập trình ứng dụng cho gợi ý (Recommender API Controllers)'),
        (r'`recommender-ai-service/app/models/recommendation_log\.py`', 'mô hình dữ liệu lưu trữ nhật ký gợi ý'),
        (r'`recommender-ai-service/inference_utils\.py`', 'tập hợp các hàm tiện ích suy luận'),
        (r'`recommender-ai-service/recommender_service/settings\.py`', 'tệp cấu hình lõi của dịch vụ AI'),
        (r'`api-gateway/gateway/views\.py`', 'bộ điều khiển tại Cổng API (API Gateway Controller)'),
        (r'`api_gateway/settings\.py`', 'cấu hình tại Cổng API'),
        (r'`docker-compose\.yml`', 'cấu hình triển khai hạ tầng ảo hóa'),
        (r'`README\.md`', 'tài liệu hướng dẫn tổng quan'),
        (r'`meta\.json`', 'tệp lưu trữ siêu dữ liệu (Metadata)'),
        (r'`r\.json`', 'định dạng phản hồi JSON'),
        (r'`book_id_map\.json`', 'từ điển ánh xạ định danh sản phẩm'),
        (r'`implicit_cf_engine\.py`', 'Lớp lõi xử lý NMF'),
        (r'`recommender_service\.py`', 'Dịch vụ Điều phối Gợi ý'),
        (r'`rag_llm\.py`', 'Thành phần xử lý RAG'),
        (r'`train_implicit_cf\.py`', 'Kịch bản huấn luyện NMF'),
        (r'`build_kb_graph_v3\.py`', 'Kịch bản xây dựng Đồ thị tri thức'),
        (r'`rag_views\.py`', 'Các API xử lý yêu cầu RAG'),
        (r'`recommender_views\.py`', 'Các API xử lý gợi ý'),
        (r'`behavior_actions\.py`', 'Định nghĩa trọng số hành vi'),
        (r'`behavior_prediction_service\.py`', 'Dịch vụ phân tích chuỗi thời gian'),
        (r'`generate_data_v4\.py`', 'Kịch bản giả lập dữ liệu'),
        (r'`train_models_v5\.py`', 'Tiến trình huấn luyện mô hình tuần tự'),
        (r'`recommendation_log\.py`', 'Mô hình Nhật ký hệ thống'),
        (r'`retriever\.py`', 'Bộ truy xuất ngữ cảnh'),
        (r'`inference_utils\.py`', 'Tiện ích hỗ trợ suy luận AI'),
        (r'`settings\.py`', 'Cấu hình hệ thống'),
        (r'`views\.py`', 'Lớp điều khiển API'),
    ]

    for pattern, repl in replacements:
        content = re.sub(pattern, repl, content)

    content = content.replace('Đây là module', 'Đây là thành phần cốt lõi')
    content = content.replace('File này', 'Thành phần này')
    content = content.replace('Code', 'Mã nguồn')
    content = content.replace('code', 'mã nguồn')
    content = content.replace('Chạy file', 'Thực thi quy trình')
    content = content.replace('chạy file', 'thực thi quy trình')

    expansion_nmf = '''

### Phân tích chuyên sâu về thuật toán Non-negative Matrix Factorization (NMF)
Thuật toán Phân tích Ma trận không âm (NMF) được áp dụng để giải quyết bài toán thưa thớt dữ liệu trong hệ thống gợi ý. Ma trận tương tác người dùng - sản phẩm $V$ (kích thước $m \\times n$) được phân rã thành hai ma trận: ma trận đặc trưng người dùng $W$ ($m \\times k$) và ma trận đặc trưng sản phẩm $H$ ($k \\times n$), với $k$ là số chiều không gian ẩn (latent space). Đặc tính "không âm" của NMF đảm bảo rằng việc biểu diễn các đặc trưng là sự kết hợp cộng dồn, giúp giải thích trực quan sở thích của khách hàng. Quá trình tối ưu hóa hàm mục tiêu Frobenius Norm được thực hiện lặp lại để giảm thiểu sai số tái tạo, từ đó tính toán được các giá trị dự đoán cho những mặt hàng mà người dùng chưa từng tương tác.

**Mã nguồn thuật toán NMF tham chiếu:**
```python
from sklearn.decomposition import NMF
import numpy as np

class ImplicitCFEngine:
    def __init__(self, n_components=20):
        self.model = NMF(n_components=n_components, init="nndsvd", random_state=42)
        
    def fit(self, user_item_matrix):
        # user_item_matrix: Ma trận tần suất tương tác thưa thớt
        W = self.model.fit_transform(user_item_matrix)
        H = self.model.components_
        return W, H
        
    def predict_user(self, user_vector):
        # Tính toán đặc trưng ẩn của người dùng mới dựa trên tương tác hiện tại
        user_latent = self.model.transform(user_vector)
        # Dự đoán điểm quan tâm đối với toàn bộ danh mục sản phẩm
        scores = np.dot(user_latent, self.model.components_)
        return scores
```
'''

    expansion_rag = '''

### Đánh giá kiến trúc Retrieval-Augmented Generation (RAG)
Mô hình RAG kết hợp sức mạnh của việc truy xuất thông tin chính xác từ Cơ sở tri thức đồ thị (Knowledge Graph) và khả năng sinh ngôn ngữ tự nhiên tự do của Mô hình ngôn ngữ lớn (LLM). Khi một truy vấn được nhận diện, hệ thống không trực tiếp gửi cho LLM mà tiến hành phân tách ngữ nghĩa, so khớp với các thực thể sản phẩm (như tác giả, thể loại, mức giá) trong đồ thị Neo4j. Đoạn văn cảnh (Context) thu được sau đó được ghép vào Prompt, đóng vai trò như một bộ nhớ ngoại vi giúp LLM hạn chế tình trạng ảo giác thông tin (Hallucination), đảm bảo tính chính xác và nhất quán trong việc tư vấn bán hàng.

**Luồng truy xuất và sinh văn bản (RAG Workflow):**
```python
class RAGPipeline:
    def __init__(self, knowledge_graph, llm_client):
        self.kg = knowledge_graph
        self.llm = llm_client
        
    def generate_response(self, user_query, session_history):
        # Bước 1: Trích xuất thực thể từ câu hỏi
        entities = extract_entities(user_query)
        
        # Bước 2: Truy xuất ngữ cảnh từ Đồ thị Neo4j
        context = self.kg.retrieve_subgraph(entities)
        
        # Bước 3: Đóng gói Prompt với ngữ cảnh
        prompt = f"""
        Dựa vào các thông tin sản phẩm có sẵn: {context}
        Và lịch sử trò chuyện: {session_history}
        Hãy trả lời câu hỏi của khách hàng: {user_query}
        """
        
        # Bước 4: Gọi Mô hình ngôn ngữ lớn (LLM) sinh phản hồi
        return self.llm.invoke(prompt)
```
'''

    content = re.sub(r'(## 2\. Hệ thống gợi ý cơ sở .*?\n)', r'\1' + expansion_nmf, content, count=1)
    content = re.sub(r'(## 3\. Hệ thống Chatbot RAG .*?\n)', r'\1' + expansion_rag, content, count=1)

    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Processed CHUONG3')
