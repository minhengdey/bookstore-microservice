# CHƯƠNG 4: TÍCH HỢP VÀ TRIỂN KHAI

Hành trình xây dựng một kiến trúc Microservices không chỉ dừng lại ở việc viết mã nguồn cho các dịch vụ riêng lẻ. Thử thách khó khăn nhất nằm ở khâu "kết dính" các dịch vụ lại với nhau thành một khối thống nhất có thể tự động giao tiếp, phục hồi sau sự cố và triển khai tự động lên các cụm máy chủ. Chương này trình bày chi tiết bức tranh toàn cảnh về cách các thành phần lõi kết nối, cơ chế nhận dạng (Authentication) thông suốt, cùng chiến lược Đóng gói (Dockerization) để tạo nên hệ sinh thái hoàn chỉnh.

## 4.1 Kiến trúc tổng thể

### 4.1.1 Mô hình hệ thống
Hệ thống sử dụng Kiến trúc Phân rã Microservices thông qua mạng Ảo hóa Containerization (Docker) và giao tiếp thông qua Message Queues (RabbitMQ). API Gateway đóng vai trò như cửa ngõ độc nhất kết nối thế giới bên ngoài với hệ sinh thái bên trong. Kiến trúc này triệt tiêu hoàn toàn sự ràng buộc cứng (Tight-Coupling) thường thấy ở các mô hình nguyên khối.

### 4.1.2 Nguyên tắc thiết kế (Design Principles)
Hệ thống tuân thủ nghiêm ngặt nguyên tắc Phòng thủ đa tầng (Defense in Depth) và Tổng hợp Dữ liệu Biên (Backend For Frontend - BFF). 
Tuyệt đối không một microservice nội bộ nào (như `order-service` hay `cart-service`) được phép mở cổng kết nối thẳng ra public Internet. Mọi luồng giao tiếp với Client phải đi qua API Gateway.

## 4.2 System Architecture

### 4.2.1 Overview & 4.2.2 Microservice Architecture
Hệ thống bao gồm 5+ Microservices chính, mỗi Microservice tự chịu trách nhiệm quản lý CSDL của riêng mình (Polyglot Persistence). Product Service và User Service sử dụng PostgreSQL cho các ràng buộc cấu trúc lõi; AI Service sử dụng Neo4j để khai thác dữ liệu Đồ thị.

### 4.2.3 API Gateway
Được xây dựng trên nền tảng NGINX Reverse Proxy kết hợp với Django Controller. Gateway làm nhiệm vụ dẫn đường (Routing), giới hạn tốc độ (Rate Limiting) và trích xuất siêu dữ liệu xác thực (Auth Introspection) trước khi điều phối tới các trạm xử lý.

### 4.2.4 Service Communication
Các Service giao tiếp hỗn hợp:
- **Giao tiếp Đồng bộ (Synchronous HTTP/REST):** Dùng cho các truy vấn Read nhanh, yêu cầu dữ liệu ngay lập tức (Ví dụ: Order hỏi Product xem mã hàng này còn tồn bao nhiêu).
- **Giao tiếp Bất đồng bộ (Asynchronous Event-driven):** Dùng RabbitMQ để phát các sự kiện thay đổi trạng thái không yêu cầu thời gian thực cực đoan (Ví dụ: Payment báo thanh toán thành công để Order cập nhật trạng thái PAID).

### 4.2.5 Containerization and Deployment
Toàn bộ mạng lưới được chuẩn hóa và ảo hóa qua `docker-compose`. Cấu hình tự động khởi chạy môi trường CSDL, Message Queue và các Application Node mà không phụ thuộc vào hệ điều hành vật lý bên ngoài.

### 4.2.6 - 4.2.9 Các cân nhắc về Bảo mật
Áp dụng cơ chế Xác thực tập trung (Centralized JWT Auth) tại lớp ngoài cùng, và kỹ thuật mã hóa nội bộ (HMAC-SHA256) tại lớp hạ tầng (Internal VNet) để tạo ra vành đai bảo mật Zero-Trust.

## 4.3 API Gateway (Nginx)

### 4.3.1 Vai trò bảo mật của NGINX
NGINX đóng vai trò như một khiên chống đạn. Nó thực hiện hai nhiệm vụ cốt tử:
1. **Chặn tấn công DDoS:** Rate Limiting được kích hoạt ở mức 10 requests / giây cho mỗi IP.
2. **Cảnh sát Xác minh:** Mọi request đều bị NGINX đánh chặn và hỏi `auth-service` xem Token có hợp lệ không thông qua `auth_request`. Nếu hợp lệ, NGINX sẽ tự động tiêm mã ID người dùng vào HTTP Headers và đẩy vào mạng nội bộ.

### 4.3.2 Cấu hình NGINX thực tế
Trích xuất mã nguồn lõi cấu hình bảo mật từ tệp `nginx.conf`:
```nginx
http {
    # Khởi tạo vùng nhớ quản lý Rate Limiting, chống DDoS
    limit_req_zone $binary_remote_addr zone=critical_api:10m rate=10r/s;

    server {
        listen 80;

        # Điểm chặn xác minh ngầm (Chỉ nội bộ Nginx gọi)
        location = /auth_verify {
            internal;
            proxy_pass http://auth-service:8000/auth/introspect/;
            proxy_pass_request_body off;
            proxy_set_header Content-Length "";
            proxy_set_header Authorization $http_authorization;
        }

        # Bảo vệ các route nhạy cảm
        location ~* ^/(orders|payment|checkout)/ {
            # Ép Nginx gọi /auth_verify trước
            auth_request /auth_verify;
            
            # Trích xuất Header từ phản hồi của Auth Service
            auth_request_set $user_id $upstream_http_x_user_id;
            
            # Áp dụng bộ lọc Rate Limit
            limit_req zone=critical_api burst=20 nodelay;
            
            # Chuyển tiếp request sạch vào mạng nội bộ với X-User-Id
            proxy_pass http://api-gateway:8000;
            proxy_set_header X-User-Id $user_id;
        }
    }
}
```

## 4.4 Xác thực với JWT (Authentication)

### 4.4.1 Cài đặt & 4.4.2 Cấu hình
JSON Web Token (JWT) là trái tim của hệ thống định danh phi trạng thái. Hệ thống sử dụng thuật toán mã hóa đối xứng phân tán `HS256`. API Gateway sau khi nhận được yêu cầu từ NGINX sẽ có nhiệm vụ bóc tách các giá trị này.

### 4.4.3 Luồng trích xuất dữ liệu
Đoạn mã xử lý Header tại API Gateway (từ dự án):
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

## 4.5 Giao tiếp giữa các Service qua RabbitMQ

### 4.5.1 Mạng lưới Bất đồng bộ & 4.5.2 Best Practice (Outbox Pattern)
Giao tiếp giữa Order Service và Payment Service (hoặc Shipping) không được diễn ra đồng bộ qua API HTTP, vì mạng luôn luôn tiềm ẩn rủi ro đứt gãy. Khi một module sập, request HTTP sẽ timeout. Do đó, hệ thống sử dụng Message Broker (RabbitMQ). Nếu Shipping Service bảo trì, các tín hiệu thanh toán vẫn được RabbitMQ ôm vào lòng và lưu xuống đĩa cứng (Persistent Mode). Khi Shipping bật lại, nó sẽ lấy các lệnh cũ ra xử lý.

Đoạn mã phát hành Sự kiện an toàn (Event Publisher) từ dự án:
```python
import pika
import json
from datetime import datetime, timezone

class EventPublisher:
    @classmethod
    def publish(cls, exchange: str, event_type: str, data: dict, version: int = 1):
        payload = {
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": version
        }
        
        channel = cls.get_channel()
        channel.basic_publish(
            exchange=exchange,
            routing_key="", # Sử dụng chế độ fanout để mọi Service cùng nghe được
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=2 # Đảm bảo Persistent Data - Lưu xuống ổ cứng
            )
        )
```

## 4.6 Docker hóa hệ thống (Containerization)

### 4.6.1 Mạng ảo hóa liên hoàn (docker-compose.yml)
Toàn bộ phức hợp CSDL, Backend, AI được khởi chạy bằng một lệnh duy nhất. Các container được nhốt chung vào mạng `bookstore-net` và sử dụng Healthcheck để đảm bảo CSDL nạp dữ liệu xong xuôi thì Backend mới bắt đầu gọi API.

Trích xuất cấu hình khởi tạo Postgres tự động từ `docker-compose.yml`:
```yaml
  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=${POSTGRES_USER:-postgres}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
    volumes:
      # Tự động nạp kịch bản khởi tạo database
      - ./scripts/init_databases.sql:/docker-entrypoint-initdb.d/init_databases.sql
      - postgres_data:/var/lib/postgresql/data
    networks:
      - bookstore-net
    healthcheck:
      # Chặn các backend khởi động trước khi DB sẵn sàng
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
```

## 4.7 Luồng hệ thống End-to-End

### 4.7.1 Kịch bản: Khách hàng mua sắm
Khách hàng duyệt Web (Product) $\\rightarrow$ Đưa hàng vào Giỏ (Cart) $\\rightarrow$ Chốt đặt đơn (Order) $\\rightarrow$ Trừ tồn kho $\\rightarrow$ Trừ tiền ngân hàng (Payment) $\\rightarrow$ Phân phối điều vận (Shipping).

### 4.7.2 Sequence logic (RabbitMQ)
1. `order-service` phát hành ID đơn hàng gửi đến Gateway.
2. Gateway định tuyến `payment-service`.
3. `payment-service` thông báo `PAYMENT_SUCCESS` lên kênh `payment_events`.
4. `shipping-service` và `order-service` cùng lúc bắt được sự kiện này để cập nhật trạng thái kho.

## 4.8 Triển khai thực tế

### 4.8.1 Triển khai Kubernetes (Optional)
Trong tương lai, nếu lưu lượng tăng đột biến, dự án có thể dễ dàng bứng nguyên khối container hiện tại sang Kubernetes (K8s). Kiến trúc Stateless JWT và RabbitMQ là điều kiện lý tưởng cho K8s tự động tăng giảm Pods.

## 4.9 Hệ thống giám sát (Logging và Monitoring)
Nhà quản trị có thể truy cập cổng `15672` của vùng chứa RabbitMQ để quản lý tình trạng tắc nghẽn luồng dữ liệu (Dead-letter exchanges).

## 4.10 Đánh giá và Kết quả Thực nghiệm

### 4.10.1 Hiệu năng và Độ trễ
Độ trễ truy vấn đọc (Read Latency) được duy trì ở mức tối thiểu nhờ In-memory Cache và cơ chế phân mảnh Database-per-service. Hệ thống không còn tình trạng chậm do DB bị khóa chéo.

### 4.10.2 Khả năng thu phóng (Scalability)
Tính độc lập tuyệt đối giữa các module. Việc `recommender-ai-service` chạy suy luận Tensor cực kỳ tốn RAM sẽ không mảy may làm ảnh hưởng đến tốc độ duyệt web của máy chủ `product-service`.

### 4.10.3 Ưu điểm
- **Chịu lỗi xuất sắc:** Một service chết không kéo sập toàn hệ thống.
- **Bảo mật:** Kiến trúc Zero-Trust ngăn chặn truy cập trái phép.
- **Tương thích cao:** Dễ dàng thay thế mô hình AI mà không phải sửa logic bán hàng.

### 4.10.4 Nhược điểm
- Đòi hỏi cấu hình máy chủ có dung lượng RAM khá lớn (trên 8GB) để chạy trơn tru mạng lưới RabbitMQ, Neo4j, và các container độc lập.
- Việc dò lỗi xuyên biên giới (Distributed Tracing) tương đối phức tạp khi có bug ở khâu đồng bộ dữ liệu sự kiện.

## 4.11 Tổng kết và Checklist Đánh giá
Qua quá trình thiết kế, tích hợp và triển khai hệ thống toàn diện, đồ án đã thỏa mãn tuyệt đối các tiêu chí kiến trúc phần mềm hiện đại:
- [x] Hệ thống thiết lập thành công API Gateway với cơ chế quét JSON Web Token (JWT) Auth trước khi đưa dữ liệu vào mạng lõi.
- [x] Hoàn thiện cấu trúc Containerization qua Docker, đồng bộ liên hoàn khối CSDL và Trí tuệ Nhân tạo.
- [x] Vận hành trơn tru luồng xử lý giao dịch tài chính (Order $\\rightarrow$ Payment $\\rightarrow$ Shipping) thông qua mạng hàng đợi tin nhắn RabbitMQ.
