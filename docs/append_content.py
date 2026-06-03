import os

ch2_path = r"d:\Study\Nam4_Ky2\KTVHTPM\ai-ktmp\Ecommerce-microservice\docs\CHUONG2_TAI_LIEU_DU_AN_ECOMMERCE_ECOM.md"
ch3_path = r"d:\Study\Nam4_Ky2\KTVHTPM\ai-ktmp\Ecommerce-microservice\docs\CHUONG3_TAI_LIEU_AI_SERVICE.md"
ch4_path = r"d:\Study\Nam4_Ky2\KTVHTPM\ai-ktmp\Ecommerce-microservice\docs\CHUONG4_TAI_LIEU_TICH_HOP_VA_TRIEN_KHAI.md"

ch2_append = """
## 6. Cơ chế Quản lý Giỏ hàng và Xử lý Giao dịch (Cart Service)

Dịch vụ giỏ hàng (Cart Service) đóng vai trò lưu trữ tạm thời các sản phẩm mà người dùng muốn mua trước khi tiến hành thanh toán. Do tính chất thay đổi liên tục của giỏ hàng, việc thiết kế dịch vụ này yêu cầu sự cẩn trọng về hiệu năng và tính nhất quán dữ liệu.

Trong tệp `cart-service/cart/services.py`, toàn bộ các thao tác thêm, sửa, xóa sản phẩm trong giỏ hàng đều được bọc trong ngữ cảnh `transaction.atomic()` của cơ sở dữ liệu.

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

Việc sử dụng `get_or_create` kết hợp với `update_fields` giúp giảm thiểu số lượng câu lệnh SQL gửi xuống cơ sở dữ liệu, tối ưu hóa tốc độ thực thi. Đặc biệt, biến `unit_price` được lưu ngay tại thời điểm thêm vào giỏ hàng để hiển thị chính xác cho khách hàng, tránh việc giá thay đổi đột ngột gây nhầm lẫn.

## 7. Cấu trúc Ủy quyền và Định tuyến tại API Gateway (BFF Layer)

Hệ thống E-commerce sử dụng mô hình Backend-For-Frontend (BFF) thông qua dịch vụ `api-gateway`. Tệp `api-gateway/gateway/views.py` chứa logic định tuyến và đóng gói dữ liệu trước khi gửi về cho giao diện người dùng.

Mỗi khi có một yêu cầu đi qua Gateway, hệ thống sẽ trích xuất các trường thông tin ủy quyền từ Header do NGINX và Auth Service truyền xuống:

```python
def _auth_headers(request) -> dict:
    '''Trích xuất các Header X-User-* từ JWT payload đã được xác thực.'''
    payload = getattr(request, "jwt_payload", None)
    if not payload:
        return {}
    return {
        "X-User-Id":   str(payload.get("user_id", "")),
        "X-User-Role": str(payload.get("role", "")),
        "X-Entity-Id": str(payload.get("entity_id", "")),
        "X-Username":  str(payload.get("username", "")),
    }
```

Nhờ cơ chế này, các dịch vụ bên dưới như Order Service hay Product Service hoàn toàn tin tưởng vào định danh người dùng mà không cần phải gọi lại Auth Service để kiểm tra Token, giúp giảm đáng kể độ trễ mạng nội bộ.
"""

ch3_append = """
## 6. Xử lý Lỗi Tối hậu và Proxy Trí tuệ Nhân tạo (AI Chat Proxy)

Trong quá trình triển khai thực tế, dịch vụ AI có thể mất thời gian để khởi động (nhất là khi nạp các mô hình mạng nơ-ron lớn vào RAM) hoặc gặp sự cố mạng tạm thời. Để đảm bảo trải nghiệm người dùng không bị gián đoạn, API Gateway đóng vai trò như một proxy trung gian xử lý các tình huống lỗi này.

**Trích xuất mã nguồn Proxy tại `api-gateway/gateway/views.py`:**
```python
@csrf_exempt
@require_POST
def ai_chat_proxy(request):
    recommender_url = f"{SVC['recommender']}/api/recommender/chat-ktmp"
    last_error = None
    
    # Cơ chế thử lại (Retry Mechanism) 3 lần
    for attempt in range(1, 4):
        try:
            # Cho phép thời gian chờ lên tới 90s vì AI model có thể đang được load
            r = requests.post(recommender_url, json=body, timeout=90)
            return JsonResponse(r.json(), status=r.status_code)
        except requests.exceptions.Timeout as e:
            last_error = e
            logger.warning(f"[AI proxy] timeout attempt={attempt}: {e}")
        except requests.exceptions.ConnectionError as e:
            last_error = e
            logger.warning(f"[AI proxy] connection attempt={attempt}: {e}")
            time.sleep(1.0) # Chờ 1 giây trước khi thử lại
            continue
            
    if isinstance(last_error, requests.exceptions.Timeout):
        return JsonResponse(
            {"error": "AI service timeout — model có thể đang tải. Vui lòng thử lại sau 10-20 giây."},
            status=504,
        )
    return JsonResponse({"error": f"AI service unavailable: {str(last_error)}"}, status=503)
```
Cơ chế Retry vòng lặp 3 lần kết hợp với `time.sleep` đảm bảo hệ thống tự động khắc phục các lỗi rớt gói tin mạng (Packet Loss) ngắn hạn mà không cần người dùng phải bấm F5 tải lại trang.

## 7. Phân tích Dữ liệu Hành vi Người dùng (Behavior Tracking)

Sức mạnh của hệ thống AI phụ thuộc hoàn toàn vào dữ liệu đầu vào. Do đó, hệ thống được thiết kế để theo dõi sát sao mọi thao tác của người dùng một cách ẩn danh và bất đồng bộ.

```python
def _track_behavior_event(request, customer_id, product_id, action):
    if customer_id is None:
        return
    if not request.session.session_key:
        request.session.create()
    try:
        headers = _auth_headers(request)
        requests.post(
            f"{SVC['recommender']}/api/recommender/events/",
            json={
                "customer_id": int(customer_id),
                "product_id": int(product_id),
                "action": action, # Ví dụ: 'view', 'add_to_cart', 'purchase'
                "session_id": request.session.session_key,
                "device": _client_device(request),
            },
            headers=headers,
            timeout=0.5, # Thời gian chờ cực ngắn để không làm chậm giao diện
        )
    except requests.exceptions.RequestException:
        pass # Bỏ qua lỗi nếu AI Service bận, ưu tiên trải nghiệm web
```
Tham số `timeout=0.5` (0.5 giây) là một thiết kế quan trọng. Việc gửi log hành vi (như Click, View) diễn ra ngầm. Nếu AI Service đang quá tải, hàm gửi log sẽ nhanh chóng bỏ cuộc và bỏ qua (Pass) thay vì làm treo trang web của khách hàng.
"""

ch4_append = """
## 6. Cơ chế Phân trang và Tối ưu Hóa Dữ liệu Trả về (Pagination and Data Formatting)

Một yếu tố kỹ thuật thường bị bỏ qua nhưng lại quyết định trực tiếp đến trải nghiệm người dùng là cơ chế phân trang (Pagination). Việc tải hàng ngàn sản phẩm cùng lúc sẽ làm sập trình duyệt của người dùng. 

Trong hệ thống E-commerce này, API Gateway chịu trách nhiệm định dạng và chuẩn hóa dữ liệu phân trang từ các Microservices trả về.

```python
def _pagination_context(payload, request, extra_query=None):
    if not isinstance(payload, dict):
        return {
            "count": len(payload) if isinstance(payload, list) else 0,
            "page": 1,
            "page_size": 10,
            "total_pages": 1,
            "search": request.GET.get("search", ""),
        }

    page_size = payload.get("page_size", 10)
    search = request.GET.get("search", "")
    prev_page = payload.get("prev_page")
    next_page = payload.get("next_page")
    
    base_params = {"page_size": page_size}
    if extra_query:
        base_params.update(extra_query)
    if search:
        base_params["search"] = search
        
    base = urlencode(base_params)
    return {
        "count": payload.get("count", 0),
        "page": payload.get("page", 1),
        "total_pages": payload.get("total_pages", 1),
        "query_for_prev": f"?page={prev_page}&{base}" if prev_page else "",
        "query_for_next": f"?page={next_page}&{base}" if next_page else "",
    }
```
Việc tạo sẵn các chuỗi truy vấn (query strings) như `query_for_next` trực tiếp tại Backend giúp mã HTML ở Frontend (Django Templates) trở nên cực kỳ tinh gọn. Lập trình viên giao diện chỉ cần gắn biến này vào thẻ thẻ thẻ liên kết `<a>` mà không cần xử lý chuỗi phức tạp.

## 7. Cơ chế Bộ đệm Tạm thời tại Tầng Gateway (In-Memory Caching)

Bên cạnh Redis, API Gateway còn triển khai một hệ thống Cache cục bộ đơn giản ngay trong bộ nhớ (In-Memory) để chặn đứng các Request trùng lặp diễn ra trong thời gian rất ngắn.

```python
_req_cache = {}
_req_cache_ttl = {}

def _get(url, request=None, cache_ttl=0, **kwargs):
    now = time.time()
    # Kiểm tra cache
    if cache_ttl > 0 and url in _req_cache:
        if now < _req_cache_ttl.get(url, 0):
            return _req_cache[url]
    
    try:
        r = requests.get(url, timeout=60, **kwargs)
        result = r.json() if r.status_code == 200 else []
        
        # Lưu cache nếu cấu hình
        if cache_ttl > 0:
            _req_cache[url] = result
            _req_cache_ttl[url] = now + cache_ttl
        
        return result
    except requests.exceptions.RequestException:
        # Cơ chế Fallback: Trả về Cache cũ ngay cả khi đã hết hạn nếu Service sập
        if url in _req_cache:
            return _req_cache[url]
        return []
```
Đoạn mã trên thể hiện tính kiên cố của hệ thống. Biến `cache_ttl` cho phép định nghĩa thời gian sống của dữ liệu. Điểm đặc biệt nhất là khối `except`: Nếu một Microservice sập, Gateway sẽ cố gắng trả về dữ liệu Cache cũ (Stale Cache) thay vì báo lỗi trắng trang, giúp khách hàng vẫn xem được danh sách sản phẩm dù CSDL đang gặp sự cố.
"""

def append_to_file(path, content):
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + content)

append_to_file(ch2_path, ch2_append)
append_to_file(ch3_path, ch3_append)
append_to_file(ch4_path, ch4_append)
print("Append successful.")
