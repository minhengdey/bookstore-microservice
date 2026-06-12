# E-Commerce Microservice

Hệ thống thương mại điện tử tách thành 8 microservices (Django), kết nối PostgreSQL trên máy host.

---

## Yêu cầu

- **Docker Desktop** (Windows/Mac) hoặc Docker + Docker Compose
- **PostgreSQL** cài sẵn trên máy (ví dụ: localhost:5432, user `postgres`)

---

## Cách chạy

### Bước 1: Cấu hình biến môi trường

```powershell
# Nếu chưa có file .env, copy từ mẫu:
copy .env.example .env

# Mở .env và sửa password PostgreSQL cho đúng với máy bạn:
# POSTGRES_PASSWORD=<mật khẩu postgres của bạn>
```

**Lưu ý:** Trong `.env` không được có comment (`#`) trên cùng dòng với giá trị (ví dụ: `KEY=value   # comment` sẽ sai).

---

### Bước 2: Tạo databases trong PostgreSQL

Kết nối PostgreSQL bằng **DBeaver** (hoặc psql) với user `postgres`, rồi chạy script:

**File:** `scripts/init_databases.sql`

Hoặc chạy từng lệnh:

```sql
CREATE DATABASE auth_db;
CREATE DATABASE user_db;
CREATE DATABASE product_db;
CREATE DATABASE cart_db;
CREATE DATABASE order_db;
CREATE DATABASE pay_db;
CREATE DATABASE ship_db;
CREATE DATABASE recommender_db;
```

---

### Bước 3: Build và chạy Docker

Mở terminal (PowerShell hoặc CMD) tại thư mục dự án:

```powershell
cd d:\Study\Nam4_Ky2\KTVHTPM\Ecommerce-microservice

# Build images (lần đầu hoặc khi đổi code)
docker compose build

# Chạy tất cả services (nền)
docker compose up -d
```

Lần đầu chạy có thể mất vài phút để build 12 images. Sau khi xong, Django trong mỗi container sẽ tự chạy `makemigrations` và `migrate` → bảng trong từng database sẽ được tạo tự động.

---

### Bước 4: Kiểm tra

- **API Gateway (web + proxy):** http://localhost:8000  
- **Các service trực tiếp:**  
  - Auth: http://localhost:8012  
  - User: http://localhost:8001  
  - Product: http://localhost:8002  
  - Cart: http://localhost:8003  
  - Order: http://localhost:8007  
  - Pay: http://localhost:8008  
  - Ship: http://localhost:8009  
  - Recommender: http://localhost:8011  

---

## Mock data (dữ liệu mẫu)

Sau khi các service đã chạy, có thể nạp dữ liệu mẫu cho tất cả bảng:

```powershell
# Chạy từ thư mục gốc project
.\scripts\seed_all.ps1

# Xóa dữ liệu cũ rồi seed lại
.\scripts\seed_all.ps1 -Clear
```

Hoặc seed từng service: `docker compose exec user-service python manage.py seed_mock` (tương tự với `product-service`, `cart-service`, ...). Thứ tự nên theo: auth → user → product → cart → order → pay → ship → recommender-ai-service.

**Tài khoản mẫu (tự tạo khi `docker compose up` qua `auth-service`):**

| Role | Username | Password | Tab đăng nhập |
|------|----------|----------|---------------|
| Quản trị | `admin` | `Admin@12345` | Quản trị |
| Khách hàng | `customer1`, `customer2`, `customer3` | `password123` | Khách hàng |
| Nhân viên | `staff1`, `staff2` | `password123` | Nhân viên |
| Quản lý | `manager1` | `password123` | Nhân viên |

Ghi đè mật khẩu qua `.env`: `DEFAULT_ADMIN_PASSWORD`, `DEFAULT_CUSTOMER_PASSWORD`, `DEFAULT_STAFF_PASSWORD`.

---

## Lệnh hữu ích

```powershell
# Xem log tất cả services
docker compose logs -f

# Xem log một service (ví dụ customer-service)
docker compose logs -f customer-service

# Dừng tất cả
docker compose down

# Dừng và xóa volumes (nếu có)
docker compose down -v
```

---

## Nếu Docker không kết nối được PostgreSQL

- Đảm bảo PostgreSQL đang chạy trên máy (localhost:5432).
- Trong `.env`: `DB_HOST=host.docker.internal` (để container trỏ về máy host).
- Nếu vẫn lỗi, mở port 5432 cho Docker:  
  **Windows:** Firewall → Inbound rule cho TCP port 5432.
