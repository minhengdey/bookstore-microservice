import os

ch2_path = r"d:\Study\Nam4_Ky2\KTVHTPM\ai-ktmp\Ecommerce-microservice\docs\CHUONG2_TAI_LIEU_DU_AN_ECOMMERCE_ECOM.md"
ch3_path = r"d:\Study\Nam4_Ky2\KTVHTPM\ai-ktmp\Ecommerce-microservice\docs\CHUONG3_TAI_LIEU_AI_SERVICE.md"
ch4_path = r"d:\Study\Nam4_Ky2\KTVHTPM\ai-ktmp\Ecommerce-microservice\docs\CHUONG4_TAI_LIEU_TICH_HOP_VA_TRIEN_KHAI.md"

ch2_append = """
## 8. Sơ đồ Tuần tự Chi tiết Luồng Mua Hàng (Checkout Flow Sequence Diagram)

Để làm rõ hơn về sự phối hợp giữa API Gateway và các Microservices trong quá trình người dùng thực hiện thanh toán, sơ đồ tuần tự dưới đây mô tả từng bước cụ thể từ lúc người dùng xác nhận giỏ hàng cho đến khi hóa đơn được tạo.

```mermaid
sequenceDiagram
    actor Client as Trình duyệt (Người dùng)
    participant Gateway as API Gateway
    participant Auth as Auth Service
    participant Cart as Cart Service
    participant Order as Order Service

    Client->>Gateway: POST /checkout (Xác nhận Đặt hàng)
    Gateway->>Auth: Xác thực Token (Nginx xử lý vòng ngoài)
    Auth-->>Gateway: Hợp lệ (Trả về X-User-Id)
    
    Gateway->>Cart: GET /carts/{customer_id}
    Cart-->>Gateway: Trả về Danh sách Sản phẩm trong Giỏ
    
    alt Giỏ hàng trống
        Gateway-->>Client: Chuyển hướng về trang Giỏ hàng kèm Lỗi
    else Giỏ hàng có sản phẩm
        Gateway->>Order: POST /orders/ (Tạo Đơn hàng Mới)
        Note right of Order: Khóa CSDL & Trừ Tồn Kho
        Order-->>Gateway: Trả về ID Đơn hàng mới (#1024)
        
        Gateway->>Cart: DELETE /carts/{customer_id} (Xóa Giỏ hàng)
        Cart-->>Gateway: Xác nhận Xóa thành công
        
        Gateway-->>Client: Chuyển hướng sang trang Thanh Toán Đơn #1024
    end
```

## 9. Bảng So sánh Khả năng Chịu lỗi giữa Kiến trúc Nguyên khối và Vi dịch vụ

Hệ thống đã chuyển đổi thành công từ kiến trúc nguyên khối sang vi dịch vụ. Bảng dưới đây cung cấp một góc nhìn tổng quan về khả năng chịu tải và chống sập đổ của kiến trúc mới so với kiến trúc cũ.

| Tiêu chí Đánh giá | Kiến trúc Nguyên khối (Monolith) | Kiến trúc Vi dịch vụ (Microservices) trong dự án |
| :--- | :--- | :--- |
| **Phạm vi Lỗi (Failure Domain)** | Một lỗi tràn RAM (Memory Leak) làm sập toàn bộ hệ thống bán hàng. | Sự cố ở Dịch vụ Đánh giá (Review) không ảnh hưởng đến luồng Đặt hàng. |
| **Quy mô Mở rộng (Scaling)** | Phải nhân bản (Scale) toàn bộ mã nguồn, tốn kém tài nguyên máy chủ. | Chỉ nhân bản những Service chịu tải lớn (ví dụ: Product Service). |
| **Tắc nghẽn CSDL (DB Bottleneck)**| Một CSDL duy nhất chịu mọi luồng Ghi/Đọc, rất dễ xảy ra Deadlock. | Áp dụng Database-per-service, triệt tiêu đụng độ giữa các miền dữ liệu. |
| **Công nghệ Lưu trữ (Polyglot)** | Bị trói buộc vào một công nghệ CSDL (ví dụ: chỉ dùng MySQL). | Sử dụng kết hợp PostgreSQL (dữ liệu lõi) và Neo4j (đồ thị tri thức). |
"""

ch3_append = """
## 8. Sơ đồ Kiến trúc Đồ thị Tri thức (Knowledge Graph Schema)

Để hình dung rõ hơn về cách dữ liệu được kết nối đa chiều, sơ đồ dưới đây mô tả các Thực thể (Nodes) và Mối quan hệ (Edges) trong cơ sở dữ liệu đồ thị Neo4j.

```mermaid
erDiagram
    USER {
        int user_id PK
        string role
    }
    PRODUCT {
        int product_id PK
        string name
        float price
    }
    CATEGORY {
        string category_name PK
    }
    
    USER ||--o{ PRODUCT : "PERFORMED (action, timestamp)"
    PRODUCT }o--|| CATEGORY : "BELONGS_TO"
    
    %% Ví dụ về sự liên kết
    %% Khách hàng -> (view/add_to_cart/purchase) -> Sách
    %% Sách -> (thuộc về) -> Danh mục
```

Sơ đồ này làm nổi bật tính ưu việt của Đồ thị Tri thức. Một node `USER` có thể có vô số đường nối (edges) tới nhiều node `PRODUCT` với các nhãn hành vi khác nhau. Từ đó, thuật toán Truy vấn Đồ thị có thể dễ dàng duyệt qua các đường nối này để tìm ra những khách hàng có hành vi tương đồng (Collaborative Filtering).

## 9. Bảng Cấu hình Siêu tham số (Hyperparameter Tuning Matrix)

Trong quá trình huấn luyện mạng BiLSTM, nhóm phát triển đã tiến hành tinh chỉnh (Fine-tuning) nhiều cấu hình siêu tham số để đạt được độ chính xác 77.30%. Bảng sau tóm tắt các tham số quan trọng nhất và tác động của chúng đối với mô hình.

| Siêu tham số (Hyperparameter) | Giá trị Tối ưu | Phân tích Tác động Kỹ thuật |
| :--- | :---: | :--- |
| **Độ dài Chuỗi (SEQ_LEN)** | 10 | Đủ dài để nắm bắt chuỗi thao tác ngắn hạn, không quá dài để tránh nhiễu thông tin (noise). |
| **Kích thước Batch (BATCH_SIZE)** | 128 | Giúp quá trình cập nhật Gradient ổn định hơn so với batch nhỏ (32), tận dụng tốt bộ nhớ VRAM. |
| **Số chiều Embedding** | 18 | Phù hợp với số lượng đặc trưng đã được trích xuất từ dữ liệu hành vi người dùng. |
| **Tỷ lệ Dropout** | 0.30 | Ngăn chặn hiện tượng học vẹt (Overfitting) khi mạng có quá nhiều trọng số. |
| **Learning Rate (Peak)** | 3e-4 | Tốc độ học tối đa trong lịch trình Warmup Cosine Decay, đảm bảo hội tụ an toàn không bị phân kỳ. |
"""

ch4_append = """
## 8. Sơ đồ Cấu trúc Mạng Ảo hóa Toàn diện (Docker Network Topology)

Quá trình triển khai không chỉ đơn thuần là việc khởi chạy các Container, mà là việc quy hoạch chúng vào các Vùng Không gian Mạng (Network Zones) bảo mật. Sơ đồ dưới đây minh họa hệ thống mạng ảo được định nghĩa trong `docker-compose.yml`.

```mermaid
flowchart TD
    Internet((Internet Khách hàng))
    
    subgraph DMZ ["Vùng Phi quân sự (Frontend Network)"]
        Nginx[Nginx Reverse Proxy]
        Gateway[API Gateway Django]
    end
    
    subgraph INTERNAL ["Mạng Nội bộ (Backend Network) - Cấm truy cập từ ngoài"]
        Auth[Auth Service]
        Prod[Product Service]
        Order[Order Service]
        AI[AI Recommender Service]
    end
    
    subgraph DATA ["Mạng Dữ liệu (Database Network)"]
        PG[(PostgreSQL Cluster)]
        Redis[(Redis Cache)]
        MQ[[RabbitMQ Message Broker]]
    end
    
    Internet -->|HTTPS / Port 80/443| Nginx
    Nginx -->|Port 8000| Gateway
    
    Gateway --> Auth
    Gateway --> Prod
    Gateway --> Order
    Gateway --> AI
    
    Auth & Prod & Order --> PG
    Prod & Gateway --> Redis
    Order --> MQ
```

Trong sơ đồ này, `PostgreSQL` và `RabbitMQ` bị giấu hoàn toàn trong lớp `DATA`. Không một truy cập trực tiếp nào từ Internet có thể chạm tới cơ sở dữ liệu. Ngay cả NGINX cũng không được phép nói chuyện trực tiếp với Database, nó bắt buộc phải đi qua các Service nghiệp vụ.

## 9. Bảng Ma trận Phân bổ Tài nguyên Container (Container Resource Allocation)

Để đảm bảo các dịch vụ không tranh giành tài nguyên của nhau, hệ thống sử dụng cơ chế cấp phát tài nguyên độc lập. Bảng dưới đây thống kê các thông số cấu hình và chính sách khởi động (Restart Policy) của các thành phần lõi.

| Tên Dịch vụ Container | Port Nội bộ | Ánh xạ Volume (Data Persistence) | Chính sách Khởi động & Ràng buộc |
| :--- | :---: | :--- | :--- |
| **PostgreSQL (db)** | 5432 | `pgdata:/var/lib/postgresql/data` | Khởi động đầu tiên, là nền tảng cốt lõi. |
| **RabbitMQ (rabbitmq)** | 5672 | `rabbitmq_data:/var/lib/rabbitmq` | `restart: always`, tự động phục hồi nếu rớt mạng. |
| **Product Service** | 8002 | Không lưu trạng thái (Stateless) | `depends_on: db, redis`, chờ CSDL sẵn sàng mới chạy. |
| **AI Recommender** | 8005 | Gắn Volume nạp Mô hình H5/Keras | Chạy nền liên tục, tiêu tốn nhiều RAM để giữ Đồ thị. |
| **API Gateway** | 8000 | Thư mục Static/Media files | Đứng phía trước các dịch vụ nghiệp vụ, kết nối ra NGINX. |

Bảng ma trận này giúp người quản trị hệ thống DevOps nắm bắt nhanh chóng trạng thái của toàn bộ kiến trúc hạ tầng mà không cần phải phân tích hàng ngàn dòng cấu hình YAML.
"""

def append_to_file(path, content):
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + content)

append_to_file(ch2_path, ch2_append)
append_to_file(ch3_path, ch3_append)
append_to_file(ch4_path, ch4_append)
print("Append diagrams and tables successful.")
