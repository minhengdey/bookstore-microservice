import re
import os

files = [
    r'd:\Study\Nam4_Ky2\KTVHTPM\ai-ktmp\Ecommerce-microservice\docs\CHUONG2_TAI_LIEU_DU_AN_ECOMMERCE_ECOM.md',
    r'd:\Study\Nam4_Ky2\KTVHTPM\ai-ktmp\Ecommerce-microservice\docs\CHUONG3_TAI_LIEU_AI_SERVICE.md',
    r'd:\Study\Nam4_Ky2\KTVHTPM\ai-ktmp\Ecommerce-microservice\docs\CHUONG4_TAI_LIEU_TICH_HOP_VA_TRIEN_KHAI.md'
]

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

for fpath in files:
    if not os.path.exists(fpath):
        continue
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    for pattern, repl in replacements:
        content = re.sub(pattern, repl, content)

    content = content.replace('Đây là file', 'Đây là thành phần cốt lõi')
    content = content.replace('File này', 'Thành phần này')
    content = content.replace('code nằm ở', 'mã nguồn được tổ chức tại')
    
    # careful with code -> mã nguồn
    # only replace when not part of words or backticks or url
    content = re.sub(r'\bCode\b(?!`)', 'Mã nguồn', content)
    content = re.sub(r'\bcode\b(?!`)', 'mã nguồn', content)
    
    # Also fix the caption format for code blocks:
    # Match patterns like: Trong tệp `cart-service/cart/services.py`, toàn bộ các thao tác...
    # and change to: **Trích xuất mã nguồn... (từ `...`):**
    # Actually, modify_ch2 didn't do this with regex, it might have been manually done or via another script. 
    # But since the user said "sửa lại docs các chương 2, 3, 4 cho tương tự form bên file ... paste code tương tự", 
    # it seems applying `modify_ch2.py` logic across the 3 files is what they want.
    
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Processed {fpath}')
