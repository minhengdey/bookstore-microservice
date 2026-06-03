import os
import re

fpath = r'd:\Study\Nam4_Ky2\KTVHTPM\ai-ktmp\Ecommerce-microservice\docs\CHUONG2_TAI_LIEU_DU_AN_ECOMMERCE_ECOM.md'
if os.path.exists(fpath):
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    replacements = [
        (r'`api-gateway/api_gateway/settings\.py`', 'cấu hình lõi của API Gateway'),
        (r'`api-gateway/gateway/views\.py`', 'lớp điều khiển giao diện (Gateway Controller)'),
        (r'`api-gateway/gateway/urls\.py`', 'tập hợp định tuyến URL của Gateway'),
        (r'`gateway/views\.py`', 'lớp điều khiển Gateway'),
        (r'`gateway/urls\.py`', 'định tuyến của Gateway'),
        (r'`gateway/middleware\.py`', 'phần mềm trung gian (Middleware) tại Gateway'),
        (r'`middleware\.py`', 'phần mềm trung gian kiểm soát truy cập'),
        (r'`_service/settings\.py`', 'tệp cấu hình dịch vụ'),
        (r'`nginx/nginx\.conf`', 'cấu hình bộ định tuyến NGINX'),
        (r'`nginx\.conf`', 'cấu hình NGINX'),
        (r'`docker-compose\.yml`', 'cấu hình triển khai hệ thống'),
        (r'`docs/API\.md`', 'tài liệu đặc tả giao diện lập trình'),
        (r'`API\.md`', 'tài liệu đặc tả API'),
        (r'`models\.py`', 'lớp mô hình dữ liệu (Data Model)'),
        (r'`views\.py`', 'lớp điều khiển API (API Controller)'),
        (r'`urls\.py`', 'tệp định tuyến (Router)'),
        (r'`serializers\.py`', 'bộ chuyển đổi dữ liệu (Serializer)'),
        (r'`permissions\.py`', 'tập hợp quy tắc phân quyền'),
        (r'`services\.py`', 'lớp xử lý nghiệp vụ lõi (Service Layer)'),
        (r'`manage\.py`', 'kịch bản quản trị hệ thống'),
        (r'`wsgi\.py`', 'cấu hình giao tiếp máy chủ web'),
        (r'`checkout\.html`', 'giao diện trang thanh toán'),
        (r'`order_pay\.html`', 'giao diện xác nhận đơn hàng'),
        (r'`rag/rag_llm\.py`', 'tích hợp mô hình ngôn ngữ lớn'),
        (r'`rag_llm\.py`', 'logic xử lý RAG'),
    ]

    for pattern, repl in replacements:
        content = re.sub(pattern, repl, content)

    content = content.replace('Đây là file', 'Đây là thành phần cốt lõi')
    content = content.replace('File này', 'Thành phần này')
    content = content.replace('code nằm ở', 'mã nguồn được tổ chức tại')
    content = content.replace('Code', 'Mã nguồn')
    content = content.replace('code', 'mã nguồn')

    expansion_arch = '''

### Đánh giá chuyên sâu về Kiến trúc Hướng Dịch vụ (Microservices Architecture)
Kiến trúc Microservices được lựa chọn nhằm giải quyết các hạn chế tồn đọng của mô hình Monolith truyền thống, đặc biệt là trong bối cảnh hệ thống thương mại điện tử đòi hỏi khả năng mở rộng (scalability) cao ở từng thành phần riêng biệt. Thay vì tập trung toàn bộ mã nguồn vào một khối duy nhất, hệ thống được phân rã thành các miền nghiệp vụ (Domain-Driven Design) độc lập như User, Product, Cart, Order và Payment. Sự phân tách này cho phép mỗi dịch vụ có thể được phát triển, triển khai và tự động thu phóng (auto-scaling) độc lập. Hơn nữa, việc áp dụng mô hình Database-per-service giúp loại bỏ hoàn toàn các điểm nghẽn cổ chai (bottlenecks) tại tầng dữ liệu, giảm thiểu rủi ro khóa chéo (deadlock) khi lưu lượng giao dịch tăng đột biến. Tuy nhiên, nó cũng đặt ra thách thức về tính toàn vẹn dữ liệu phân tán (Distributed Data Integrity), buộc hệ thống phải áp dụng mẫu thiết kế SAGA và Outbox Pattern thông qua hệ thống RabbitMQ để đảm bảo tính nhất quán cuối cùng (Eventual Consistency).
'''
    
    expansion_auth = '''

### Cơ chế Xác thực và Phân quyền (Authentication & Authorization)
Trong hệ thống phân tán, việc xác thực yêu cầu được thực hiện tập trung tại Cổng API Gateway nhằm giảm tải cho các vi dịch vụ phía sau. Hệ thống sử dụng cơ chế JSON Web Token (JWT) theo tiêu chuẩn RFC 7519, giúp quá trình xác thực ở trạng thái vô trạng (stateless). Khi người dùng đăng nhập thành công, Dịch vụ Xác thực (Auth Service) sẽ phát sinh một cặp Access Token và Refresh Token, ký bằng thuật toán HMAC-SHA256 hoặc RSA. Bất kỳ yêu cầu (request) nào đi vào API Gateway đều bị chặn lại bởi lớp Middleware để kiểm tra chữ ký số (Signature) và thời gian sống (Expiration). Nếu hợp lệ, hệ thống sẽ tự động gán thêm các thông tin định danh nội bộ (như X-User-Id) vào Header và chuyển tiếp yêu cầu đến các dịch vụ đích. Phương pháp này hoàn toàn cách ly các token bên ngoài với logic nội bộ, tuân thủ nguyên tắc Không tin tưởng tuyệt đối (Zero-Trust Architecture).

**Mã nguồn Middleware Xác thực tiêu biểu:**
```python
import jwt
from django.conf import settings
from django.http import JsonResponse

class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                # Giải mã và xác thực chữ ký token
                payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
                
                # Truyền định danh người dùng xuống các dịch vụ nội bộ
                request.META['HTTP_X_USER_ID'] = str(payload['user_id'])
                request.META['HTTP_X_ROLE'] = payload.get('role', 'customer')
                
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token đã hết hạn'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token không hợp lệ'}, status=401)

        response = self.get_response(request)
        return response
```
'''

    content = re.sub(r'(## 1\. Tổng quan hệ thống .*?\n)', r'\1' + expansion_arch, content, count=1)
    content = re.sub(r'(## 3\. Kiến trúc Dịch vụ xác thực và Người dùng .*?\n)', r'\1' + expansion_auth, content, count=1)

    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Processed CHUONG2')
