import os
import re

def write_ch2():
    content = """# Chương 2: Phát triển Hệ E-Commerce Microservices

## 2.1 Xác định yêu cầu
### 2.1.1 Functional Requirements
- **Xác thực và Cấp phép Phi trạng thái (Stateless Authentication):** Hệ thống kiên quyết loại bỏ cơ chế Cookie/Session truyền thống lưu trên RAM máy chủ. Việc lưu trữ trạng thái người dùng tại máy chủ sẽ bóp nghẹt khả năng nhân bản (Scale-out) máy chủ. Thay vào đó, nền tảng sử dụng JSON Web Token (JWT).
- **Quản lý Vòng đời Giỏ hàng Đa nền tảng (Omnichannel Cart):** Giỏ hàng phải được duy trì liên tục và đồng bộ hóa ngay lập tức.
- **Thanh toán tích hợp và Chống Mua lố (Overselling Prevention):** Luồng thanh toán cần liên kết động với các Gateway Tài chính bên thứ ba. Hệ thống phải sở hữu chức năng khấu trừ Tồn kho tạm thời (Reserve Stock) ngay khi người dùng bấm nút "Tiến hành Thanh toán".
- **Phân quyền vai trò (Role-Based Access Control - RBAC):** Kiến trúc phân quyền mềm dẻo. Chỉ những tài khoản mang nhãn `staff`, `manager` hoặc `admin` mới được truy cập vào các giao diện Dashboard quản trị.

### 2.1.2 Non-functional Requirements
- **Hiệu năng và Tốc độ Đọc (Read-Heavy Performance):** Thời gian phản hồi API dưới 200ms cho các truy vấn xem danh sách sản phẩm là điều kiện tiên quyết. Hệ thống phải chịu tải được 10.000 Requests Per Second (RPS) vào các dịp Flash Sale lớn.
- **Tính Chịu lỗi (Fault Tolerance) & Trống phân mảnh (Resilience):** Hệ thống được thiết kế theo tư duy bi quan (Pessimistic Design). Khách vẫn phải thao tác mua được hàng và trừ tiền bình thường, email sẽ tự động được gửi bù khi dịch vụ phục hồi nhờ vào mạng hàng đợi.
- **Tính Nhất quán Cuối cùng (Eventual Consistency):** Theo định lý CAP, hệ thống chấp nhận dữ liệu cập nhật chậm (độ trễ khoảng 1-2 giây) giữa các vi dịch vụ để đổi lấy khả năng tự động thu phóng vô hạn ở mức máy chủ mà không bị khóa (Lock) cơ sở dữ liệu.

## 2.2 Phân rã hệ thống theo DDD
### 2.2.1 Bounded Context
Dự án tiến hành xác định các Vùng Không gian Giới hạn (Bounded Contexts) để chặt hệ thống nguyên khối thành **5 Microservices** cực kỳ chuyên biệt:
- **User/Auth Service (Identity & Access):** Miền dữ liệu chỉ xoay quanh định danh người dùng (Identity), Vai trò (Role) và Mật mã (Credentials).
- **Product Service (Catalog & Inventory):** Xử lý danh mục (Catalog), siêu dữ liệu sách (Metadata), và lượng Tồn kho vật lý (Physical Stock).
- **Cart Service (Ephemeral Shopping):** Miền dữ liệu tạm thời. Hoạt động với tần suất Ghi/Xóa cực kỳ dày đặc.
- **Order Service (Sales & Fulfillment):** Quản lý chu trình sống (Lifecycle) của hóa đơn từ lúc Khởi tạo (Pending) đến Giao hàng (Shipped).
- **Payment Service (Financial Transactions):** Miền giao tiếp ngoại vi. Không chứa logic bán hàng nội bộ.

### 2.2.2 Nguyên tắc
Kiến trúc Microservices được lựa chọn nhằm giải quyết các hạn chế tồn đọng của mô hình Monolith truyền thống, đặc biệt là trong bối cảnh hệ thống thương mại điện tử đòi hỏi khả năng mở rộng (scalability) cao ở từng thành phần riêng biệt. Việc áp dụng mô hình Database-per-service giúp loại bỏ hoàn toàn các điểm nghẽn cổ chai (bottlenecks) tại tầng dữ liệu, giảm thiểu rủi ro khóa chéo (deadlock) khi lưu lượng giao dịch tăng đột biến.

## 2.3 Thiết kế Product Service (Django)
### 2.3.1 Data Model
Viết code:
```python
class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = "categories"

class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="VND")
    sku = models.CharField(max_length=50, unique=True, null=True, blank=True)
    attributes = models.JSONField(default=dict)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, default="active")
    stock = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
```

### 2.3.2 Book (Sub-domain)
Thuộc tính sách được tổ chức trong trường `attributes` kiểu JSON của model `Product`, ví dụ như:
```json
{
  "author": "Nguyễn Nhật Ánh",
  "pages": 300,
  "publisher": "NXB Trẻ"
}
```

### 2.3.3 Electronics & Fashion
Tương tự như sách, các thuộc tính của nhóm hàng điện tử và thời trang (ví dụ như `warranty`, `size`, `color`) cũng được tổ chức mềm dẻo thông qua trường `attributes` (JSONField).

### 2.3.4 API
- `GET /api/products/`: Lấy danh sách sản phẩm.
- `GET /api/products/{id}/`: Lấy chi tiết một sản phẩm.

## 2.4 Thiết kế User Service (Django)
### 2.4.1 Phân loại người dùng
Trong hệ thống này, các role bao gồm `customer`, `staff`, `manager` và `admin`. Việc quản lý role được xử lý trực tiếp bởi Auth Service và API Gateway sẽ trích xuất token.

### 2.4.2 Model
Viết code:
```python
# Cấu trúc JSON Web Token (JWT) cho User
# Trích xuất Header từ JWT payload
payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
request.META['HTTP_X_USER_ID'] = str(payload['user_id'])
request.META['HTTP_X_ROLE'] = payload.get('role', 'customer')
```

### 2.4.3 Phân quyền (RBAC)
Chỉ những tài khoản mang nhãn `staff`, `manager` hoặc `admin` mới được truy cập vào các giao diện Dashboard quản trị. Cơ chế này được xử lý thông qua Middleware Xác thực tại API Gateway để chặn request rác.

### 2.4.4 API
- `POST /auth/login/`: Xác thực người dùng, trả về JWT token.
- `POST /auth/register/`: Đăng ký người dùng mới.

## 2.5 Thiết kế Cart Service
### 2.5.1 Giỏ hàng
Giỏ hàng được quản lý dưới dạng In-memory tạm thời hoặc lưu vào DB với tần suất đọc/ghi cao, không mang tính pháp lý (Mất giỏ hàng cũng không sao).

### 2.5.2 Logic
Viết code:
```python
def add_item(self, customer_id: int, product_id: int, quantity: int, unit_price: float = 0):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than 0")
        
    with transaction.atomic():
        cart = self.get_cart(customer_id)
        item, created = CartItem.objects.get_or_create(
            cart=cart, product_id=product_id,
            defaults={"quantity": quantity, "unit_price": unit_price}
        )
        
        if not created:
            item.quantity += quantity
            item.unit_price = unit_price # Cập nhật giá mới nhất
            item.save(update_fields=["quantity", "unit_price"])
            
    return self.get_cart(customer_id)
```

## 2.6 Thiết kế Order Service
### 2.6.1 Trạng thái đơn hàng
Hóa đơn trải qua vòng đời từ lúc Khởi tạo (`PENDING`) đến khi thanh toán thành công (`PAID`), bị hủy (`CANCELLED`) hoặc giao hàng thành công.

### 2.6.2 Model & 2.6.3 API
Hệ thống sử dụng kỹ thuật Pessimistic Lock kết hợp Sắp xếp Tối ưu để trừ tồn kho an toàn:
Viết code:
```python
# Trích xuất mã nguồn hàm trừ tồn kho an toàn
items = sorted(items, key=lambda x: x["product_id"])
with transaction.atomic():
    product_ids = [item["product_id"] for item in items]
    products = Product.objects.select_for_update().filter(id__in=product_ids)
    
    # ... xác thực tồn kho
    for item in items:
        # Cập nhật số lượng
        product.stock -= item["quantity"]
        product.save(update_fields=["stock"])
```

## 2.7 Payment Service (Mocking)
### 2.7.1 Logic thanh toán
Khi người dùng xác nhận thanh toán, Payment Service sẽ thực hiện trừ tiền và gửi một sự kiện `PAYMENT_SUCCESS` thông qua mạng RabbitMQ. 

## 2.8 Shipping Service (Mocking)
### 2.8.1 Logic giao hàng & 2.8.2 Trạng thái
Dịch vụ vận chuyển (Shipping Service) hoạt động độc lập, lắng nghe các sự kiện đơn hàng đã thanh toán để điều phối vận chuyển.

### 2.8.3 API
- Các sự kiện và API giả lập điều phối trạng thái giao hàng từ hệ thống kho.

## 2.9 Luồng hệ thống tổng thể

Dưới đây là một số biểu đồ tổng quan cho hệ thống đã thiết kế:

```mermaid
usecaseDiagram
    actor Khách_Hàng_Mua_Sắm
    actor Quản_Trị_Viên_Hệ_Thống
    
    package Hệ_thống_Bán_lẻ_Trực_tuyến {
        usecase "Đăng ký / Đăng nhập / Quản lý Hồ sơ" as UC1
        usecase "Tìm kiếm, Lọc và Duyệt Sản phẩm" as UC2
        usecase "Quản lý Giỏ hàng (Thêm/Sửa/Xóa)" as UC3
        usecase "Tiến hành Đặt hàng & Thanh toán" as UC4
        usecase "Theo dõi Lịch sử và Trạng thái Đơn" as UC5
        
        usecase "Quản trị Danh mục và Sản phẩm" as UC6
        usecase "Kiểm soát Số lượng Tồn kho" as UC7
        usecase "Quản lý và Duyệt Đơn hàng" as UC8
        usecase "Phân tích Thống kê Doanh thu" as UC9
    }
    
    Khách_Hàng_Mua_Sắm --> UC1
    Khách_Hàng_Mua_Sắm --> UC2
    Khách_Hàng_Mua_Sắm --> UC3
    Khách_Hàng_Mua_Sắm --> UC4
    Khách_Hàng_Mua_Sắm --> UC5
    
    Quản_Trị_Viên_Hệ_Thống --> UC1
    Quản_Trị_Viên_Hệ_Thống --> UC6
    Quản_Trị_Viên_Hệ_Thống --> UC7
    Quản_Trị_Viên_Hệ_Thống --> UC8
    Quản_Trị_Viên_Hệ_Thống --> UC9
    
    %% Mối quan hệ rẽ nhánh và bắt buộc
    UC4 .> UC3 : <<include>> (Yêu cầu phải có giỏ hàng)
    UC2 .> UC1 : <<extend>> (Người dùng vô danh vẫn xem được)
```

```mermaid
sequenceDiagram
    autonumber
    actor User as Khách hàng
    participant API as Cổng API (API Gateway)
    participant Product as Dịch vụ Sản phẩm
    participant Order as Dịch vụ Đơn hàng
    participant Pay as Dịch vụ Thanh toán
    participant MQ as Mạng Hàng Đợi (RabbitMQ)

    Note over User, API: GIAI ĐOẠN 1: Chuẩn bị giao dịch (Prepare Phase)
    User->>API: Gửi lệnh `POST /checkout` với Payload Giỏ Hàng
    
    API->>Product: Gửi lệnh `Khóa Tồn Kho` (Reserve Stock) cho ID Sách và Số lượng
    alt Kho vật lý hết hàng
        Product-->>API: 400 Bad Request (Lỗi: Tồn kho không đủ)
        API-->>User: Hiển thị lỗi thông báo (Hủy toàn bộ giao dịch ngay từ đầu)
    else Kho vật lý đủ hàng
        Product->>Product: Khóa ROW, trừ stock trong CSDL
        Product-->>API: 200 OK (Đã giữ chỗ, giấu số lượng khỏi khách hàng khác)
    end
    
    Note over API, Order: GIAI ĐOẠN 2: Khởi tạo Hóa đơn (Pending State)
    API->>Order: Gửi lệnh tạo Hóa đơn mới với trạng thái PENDING
    Order-->>API: Trả về Mã Hóa Đơn #ORD-999
    
    Note over User, Pay: GIAI ĐOẠN 3: Xử lý Tài chính (Payment Gateway)
    User->>Pay: Nhập thông tin Thẻ Tín dụng / Ví điện tử
    Pay->>Pay: Xác thực trừ tiền thành công trong CSDL nội bộ
    Pay-->>User: Màn hình Xanh - Giao dịch thành công (Client yên tâm thoát trang)
    
    Note over Pay, MQ: GIAI ĐOẠN 4: Lan truyền Sự kiện (Eventual Consistency)
    Pay->>MQ: [Phát Sự Kiện] `PAYMENT_SUCCESS (#ORD-999)` thông qua Outbox
    
    par Luồng xử lý song song bất đồng bộ
        MQ->>Order: Lắng nghe sự kiện, truy vấn CSDL đổi Trạng thái Đơn hàng thành PAID
        MQ->>Product: Lắng nghe sự kiện, đánh dấu bản log Stock thành COMMITTED
    end
```

```mermaid
erDiagram
    %% KHỐI AUTH/USER DATABASE (Cách ly hoàn toàn về bảo mật)
    AUTH_DB_USER {
        UUID id PK "Mã định danh duy nhất (UUIDv4)"
        varchar username
        varchar hashed_password
        varchar email "Unique Index"
    }
    
    %% KHỐI PRODUCT DATABASE (Trung tâm tham chiếu dữ liệu lõi)
    PRODUCT_DB_ITEM {
        int id PK
        varchar title
        decimal price "Giá thay đổi theo thị trường"
        int stock "Tồn kho thực tế đang nằm trong kho"
    }
    
    STOCK_RESERVATION_LOG {
        int id PK
        int order_id "Mã đơn hàng"
        int quantity "Số lượng bảo lưu"
        varchar status "RESERVED, RELEASED, COMMITTED"
    }
    
    %% KHỐI ORDER DATABASE (Lưu trữ giao dịch - Sổ cái Kế toán)
    ORDER_DB_RECORD {
        int id PK
        UUID customer_uuid "Tham chiếu mềm sang Auth DB"
        decimal total_amount
        varchar order_status "ENUM: PENDING, PAID, CANCELLED"
    }
    
    ORDER_DB_LINE_ITEM {
        int id PK
        int order_id FK "Ràng buộc cứng CÙNG DB"
        int product_id "Tham chiếu mềm sang Product DB"
        int buy_quantity
        decimal locked_price "Giá chốt tại thời điểm mua hàng"
    }
    
    ORDER_DB_RECORD ||--|{ ORDER_DB_LINE_ITEM : Bao_gồm
    PRODUCT_DB_ITEM ||--o{ STOCK_RESERVATION_LOG : Log_kho
    PRODUCT_DB_ITEM ||..o{ ORDER_DB_LINE_ITEM : Mối_nối_logic
    AUTH_DB_USER ||..o{ ORDER_DB_RECORD : Mối_nối_logic
```

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

## 2.10 Hướng dẫn thực hành
### 2.10.1 Mục tiêu
Sinh viên cần thiết kế sơ đồ, cấu trúc CSDL và mapping chuẩn xác để hệ thống hoạt động thống nhất.

### 2.10.2 Hướng dẫn vẽ Class Diagram bằng Visual Paradigm
Để sinh ra mô hình tương tự như Visual Paradigm, chúng ta có thể sử dụng biểu đồ Class Diagram từ Mermaid:

Viết script (Mermaid Code):
```mermaid
classDiagram
    class Product {
        +int id
        +String name
        +Decimal price
        +int stock
        +reserve_stock()
    }
    class Category {
        +int id
        +String name
        +String description
    }
    class Order {
        +int id
        +UUID customer_uuid
        +Decimal total_amount
        +String status
        +create_order()
    }
    class CartItem {
        +int id
        +int product_id
        +int quantity
    }
    
    Product "1" -- "many" Category : belongs to
    Order "1" -- "many" CartItem : contains
```

### 2.10.3 Mapping Class Diagram sang Database & 2.10.4 Thiết kế Database cho từng Service
Sử dụng mô hình Database-per-service (Mỗi dịch vụ một Database riêng). Tham chiếu giữa các dịch vụ (ví dụ từ Order sang Product) sử dụng liên kết mềm (soft-link) qua Product ID chứ không dùng khóa ngoại (Foreign Key) vật lý.

### 2.10.5 So sánh MySQL vs PostgreSQL
Hệ thống sử dụng PostgreSQL nhờ tính năng `JSONB` hỗ trợ lưu trữ metadata (`attributes`) cực kỳ nhanh và mềm dẻo.

### 2.10.6 Bài tập & 2.10.7 Checklist đánh giá
- [x] Có API Gateway
- [x] Có JWT Auth
- [x] Có sơ đồ class đúng UML
- [x] Database tách riêng từng service

## 2.11 Kết luận
- Kiến trúc microservices giúp hệ thống xử lý giao dịch linh hoạt và ngăn chặn hiện tượng thắt cổ chai ở CSDL.
- DDD giúp chia tách ranh giới rõ ràng (Bounded Contexts) ngay từ đầu.
- SAGA và Event-Driven (với RabbitMQ) là nền móng để giải quyết Distributed Transaction.
"""
    with open(r'd:\Study\Nam4_Ky2\KTVHTPM\ai-ktmp\bookstore-microservice\docs\CHUONG2_TAI_LIEU_DU_AN_BOOKSTORE_ECOM.md', 'w', encoding='utf-8') as f:
        f.write(content)

def write_ch3():
    content = """# Chương 3: AI Service cho tư vấn sản phẩm

## 3.1 Mục tiêu
Xây dựng hệ thống AI gợi ý sản phẩm dựa trên:
- Hành vi người dùng (click, search, add-to-cart)
- Quan hệ sản phẩm (similarity) qua Đồ thị tri thức
- Ngữ cảnh truy vấn (chatbot đàm thoại)

Output:
- Danh sách sản phẩm đề xuất (Recommendation List)
- Chatbot tư vấn giải đáp

## 3.2 Kiến trúc AI Service
AI Service được thiết kế như một microservice độc lập kết nối qua API nội bộ:
- **Input:** user behavior (chuỗi thao tác theo thời gian), query của người dùng
- **Processing:**
  - Sequence Model (BiLSTM Attention)
  - Knowledge Graph (Neo4j)
  - RAG (Retrieval-Augmented Generation)
- **Output:** recommendation list, chatbot response

## 3.3 Thu thập dữ liệu
### 3.3.1 User Behavior Data
Hệ thống AI xử lý dữ liệu hành vi chuỗi thời gian (Time-series data) như: thao tác `view`, `click`, `add_to_cart`, `purchase`, `wishlist`, `remove_from_cart`, `search`, `review`.

### 3.3.2 Ví dụ dataset
Bộ dữ liệu gồm hàng trăm ngàn bản ghi dưới dạng CSV, mỗi dòng ghi nhận: `user_id`, `session_id`, `product_id`, `action`, `timestamp`, `device`.

## 3.4 Mô hình LSTM (Sequence Modeling)
### 3.4.1 Ý tưởng
Mọi tương tác của người dùng trên web không phải là các sự kiện ngẫu nhiên rời rạc, mà là một chuỗi tuần tự theo thời gian tuân theo chuỗi Markov tiềm ẩn. Mạng BiLSTM (Bidirectional LSTM) sẽ quan sát chuỗi hành động này cả từ quá khứ đến hiện tại để nhận diện hành vi kế tiếp.

### 3.4.2 Model chi tiết
Viết code:
```python
def build_bilstm_attention_model(in_shape, NUM_CLASSES):
    inp = layers.Input(shape=in_shape)
    x   = layers.LayerNormalization()(inp)   
    x   = layers.Bidirectional(layers.LSTM(256, return_sequences=True))(x)
    x   = layers.LayerNormalization()(x)
    x   = layers.Dropout(0.30)(x)
    
    x   = layers.Bidirectional(layers.LSTM(128, return_sequences=True))(x)
    attn = MultiHeadSelfAttention(256, num_heads=4)(x)
    x    = layers.Add()([x, attn]) 
    x    = layers.LayerNormalization()(x)
    
    x    = layers.GlobalAveragePooling1D()(x)
    x    = layers.Dense(256, activation="gelu")(x) 
    x    = layers.Dropout(0.25)(x)
    x    = layers.Dense(128, activation="gelu")(x)
    x    = layers.Dropout(0.15)(x)
    
    out  = layers.Dense(NUM_CLASSES, activation="softmax", dtype="float32")(x)
    m    = Model(inp, out, name="BiLSTM_Attention")
    return m
```

### 3.4.3 Training
Sử dụng bộ lập lịch thay đổi tốc độ học theo `WarmupCosineDecay`:
Viết code:
```python
class WarmupCosineDecay(Callback):
    def on_epoch_begin(self, epoch, logs=None):
        if epoch < self.warmup_epochs:
            lr = self.min_lr + (self.peak_lr - self.min_lr) * epoch / max(self.warmup_epochs - 1, 1)
        else:
            progress = (epoch - self.warmup_epochs) / max(self.total_epochs - self.warmup_epochs, 1)
            lr = self.min_lr + 0.5 * (self.peak_lr - self.min_lr) * (1 + math.cos(math.pi * progress))
            
        tf.keras.backend.set_value(self.model.optimizer.lr, lr)
```

## 3.5 Knowledge Graph với Neo4j
### 3.5.1 Mô hình đồ thị
Ánh xạ các tương tác mua bán thành các cạnh đồ thị (Edges) kết nối giữa `USER`, `PRODUCT` và `CATEGORY`.

### 3.5.2 Ví dụ Cypher
Viết code (Tạo đồ thị tự động bằng Python NetworkX):
```python
import networkx as nx
G = nx.MultiDiGraph()
# 1. Thêm Nút User và Nút Product
for uid in df["user_id"].unique():
    G.add_node(uid, label="User")

# 2. Tạo Liên kết (Edges) thể hiện Ngữ nghĩa Bán lẻ
for _, row in chunk.iterrows():
    # Khách hàng A -> [Đã Mua] -> Sản phẩm B
    G.add_edge(row["user_id"], row["product_id"],
               relation="PERFORMED",
               action=row["action"])
    # Sản phẩm B -> [Thuộc Về] -> Danh mục
    G.add_edge(row["product_id"], row["category"],
               relation="BELONGS_TO")
```

### 3.5.3 Truy vấn gợi ý
Neo4j Graph hỗ trợ truy vấn các hành vi của những khách hàng tương đồng (Collaborative Filtering).

## 3.6 RAG (Retrieval-Augmented Generation)
Kết hợp Đồ thị Tri thức để lấy Context nhằm chặn ảo giác cho Chatbot LLM.

Viết code:
```python
class RAGChatLLM:
    def _build_context(self, user_id: str) -> dict:
        history  = self.rag.retrieve_user_history(user_id, top_k=8)
        recs     = self.rag.recommend_products(user_id) # Khởi chạy suy luận BiLSTM
        similar  = self.rag.retrieve_similar_users(user_id, top_k=3)
        return {
            "user_id": user_id,
            "history": history,
            "recommendations": recs.get("recommendations", [])[:6]
        }
        
    def _fallback(self, message: str, ctx: dict) -> str:
        # Xử lý khi API LLM hết hạn ngạch
        if any(k in message.lower() for k in ["gợi ý","recommend"]):
            return f"Dựa trên lịch sử, tôi gợi ý bạn..."
        return "Xin chào, hệ thống hiện đang bận..."
```
"""
    with open(r'd:\Study\Nam4_Ky2\KTVHTPM\ai-ktmp\bookstore-microservice\docs\CHUONG3_TAI_LIEU_AI_SERVICE.md', 'w', encoding='utf-8') as f:
        f.write(content)

def write_ch4():
    content = """# Chương 4: Tích hợp và Triển khai

## 4.1 Kiến trúc tổng thể
### 4.1.1 Mô hình hệ thống
Hệ thống sử dụng Kiến trúc Phân rã Microservices thông qua mạng Ảo hóa (Containerization) và giao tiếp Message Queues.

### 4.1.2 Nguyên tắc
Tuân thủ nguyên tắc Phòng thủ đa tầng (Defense in Depth) và Tổng hợp Dữ liệu Biên (Backend For Frontend). Không service nào được mở kết nối thẳng với Internet.

## 4.2 System Architecture
### 4.2.1 Overview & 4.2.2 Microservice Architecture
Hệ thống gồm 5+ Microservices chính, hoạt động trên các CSDL phân mảnh độc lập (Polyglot Persistence).

### 4.2.3 API Gateway
Sử dụng Django kết hợp NGINX Reverse Proxy chặn phía trước cổng hệ thống.

### 4.2.4 Service Communication
Các Service giao tiếp bất đồng bộ qua hệ thống Event-driven (RabbitMQ).

### 4.2.5 Containerization and Deployment
Triển khai nguyên cụm hệ thống tự động hóa qua `docker-compose.yml`.

### 4.2.6 - 4.2.9 Design Principles, Security, Discussion
Áp dụng cơ chế Xác thực (Auth) tập trung tại API Gateway và kỹ thuật mã hóa nội bộ (HMAC-SHA256) giữa các service với nhau để tạo vành đai bảo mật Zero-Trust.

## 4.3 API Gateway (Nginx)
### 4.3.1 Vai trò
Chặn mọi yêu cầu trái phép, phòng chống tấn công DDoS (Rate Limiting) và đóng vai trò như chốt kiểm soát Auth chung.

### 4.3.2 Cấu hình mẫu
Viết code:
```nginx
http {
    limit_req_zone $binary_remote_addr zone=critical_api:10m rate=10r/s;

    server {
        listen 80;

        location = /auth_verify {
            internal;
            proxy_pass http://auth-service:8000/auth/introspect/;
            proxy_pass_request_body off;
            proxy_set_header Content-Length "";
            proxy_set_header Authorization $http_authorization;
        }

        location ~* ^/(orders|payment|checkout)/ {
            auth_request /auth_verify;
            auth_request_set $user_id $upstream_http_x_user_id;
            
            limit_req zone=critical_api burst=20 nodelay;
            proxy_pass http://api-gateway:8000;
            proxy_set_header X-User-Id $user_id;
        }
    }
}
```

## 4.4 Authentication (JWT)
### 4.4.1 Cài đặt & 4.4.2 Cấu hình
Sử dụng thuật toán mã hóa đối xứng phân tán cho JSON Web Token.

### 4.4.3 Luồng
Viết code:
```python
def _auth_headers(request) -> dict:
    '''Trích xuất các Header X-User-* từ JWT payload đã được xác thực.'''
    payload = getattr(request, "jwt_payload", None)
    if not payload:
        return {}
    return {
        "X-User-Id":   str(payload.get("user_id", "")),
        "X-User-Role": str(payload.get("role", "")),
        "X-Username":  str(payload.get("username", "")),
    }
```

## 4.5 Giao tiếp giữa các Service
### 4.5.1 REST API call & 4.5.2 Best Practice
Sử dụng RabbitMQ với Outbox Pattern để cam kết phân phối dữ liệu an toàn.

Viết code:
```python
class EventPublisher:
    @classmethod
    def publish(cls, exchange: str, event_type: str, data: dict, version: int = 1):
        payload = {
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        channel = cls.get_channel()
        channel.basic_publish(
            exchange=exchange,
            routing_key="", # Sử dụng chế độ fanout
            body=json.dumps(payload),
            properties=pika.BasicProperties(delivery_mode=2) # Persistent Data
        )
```

## 4.6 Docker hóa hệ thống
### 4.6.1 Dockerfile (Django) & 4.6.2 docker-compose.yml
Viết code:
```yaml
  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=${POSTGRES_USER:-postgres}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
    volumes:
      - ./scripts/init_databases.sql:/docker-entrypoint-initdb.d/init_databases.sql
      - postgres_data:/var/lib/postgresql/data
    networks:
      - bookstore-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
```

## 4.7 Luồng hệ thống (End-to-End)
### 4.7.1 Use case: Mua hàng
Người dùng duyệt web $\\rightarrow$ thêm hàng vào giỏ $\\rightarrow$ chốt đơn hàng $\\rightarrow$ thanh toán $\\rightarrow$ xử lý đóng gói và giao hàng.

### 4.7.2 Sequence logic
- `order-service` gọi `payment-service` thông qua API Gateway.
- Khi thanh toán thành công, `payment-service` broadcast sự kiện lên RabbitMQ $\\rightarrow$ `shipping-service` bắt được để vận chuyển.

## 4.8 Triển khai Kubernetes (Optional)
### 4.8.1 Deployment & 4.8.2 Service
Sử dụng Docker Swarm / Kubernetes để cấu hình tự động phân phối dịch vụ nếu cần tải lớn (ví dụ: nhân bản `product-service`).

## 4.9 Logging và Monitoring
- Giám sát luồng message chạy qua RabbitMQ qua trang quản trị của `rabbitmq:management`.

## 4.10 Đánh giá hệ thống
### 4.10.1 Hiệu năng
Độ trễ thấp nhờ vào API Gateway Cache và In-memory Singleton Graph tại máy chủ AI.

### 4.10.2 Khả năng mở rộng
Việc scale từng service diễn ra độc lập, không gặp hiện tượng dẫm chân lên nhau.

### 4.10.3 Ưu điểm & 4.10.4 Nhược điểm
**Ưu điểm:** Khả năng chịu lỗi cao, kiến trúc tách bạch, AI Recommender dễ dàng cập nhật model.
**Nhược điểm:** Đòi hỏi cấu hình DevOps và RAM server khá lớn để chạy nền RabbitMQ và Neo4j.

## 4.11 Bài tập thực hành
- Test toàn bộ luồng mua hàng thực tế (Order Flow) 
- Test kết quả gợi ý sản phẩm và nói chuyện với Chatbot (AI integration flow).

## 4.12 Checklist đánh giá
- [x] Có API Gateway & JWT Auth
- [x] Có Docker chạy được liên hoàn toàn khối CSDL và AI
- [x] Có luồng đặt hàng (order $\\rightarrow$ payment $\\rightarrow$ shipping) qua RabbitMQ
"""
    with open(r'd:\Study\Nam4_Ky2\KTVHTPM\ai-ktmp\bookstore-microservice\docs\CHUONG4_TAI_LIEU_TICH_HOP_VA_TRIEN_KHAI.md', 'w', encoding='utf-8') as f:
        f.write(content)

write_ch2()
write_ch3()
write_ch4()
print("Done writing Chapter 2, 3, 4")
