# SQL Seed – Dữ liệu mẫu theo từng bảng/DB

Các file trong thư mục này chèn dữ liệu mẫu vào **từng database** (mỗi file một DB). Dùng khi bạn muốn import bằng **DBeaver** hoặc **psql** thay vì chạy Django `seed_mock`.

## Thứ tự chạy (theo số thứ tự file)

| # | File | Database | Bảng được chèn |
|---|------|----------|----------------|
| 01 | `01_customer_db_seed.sql` | customer_db | users, customers, web_addresses |
| 02 | `02_catalog_db_seed.sql` | catalog_db | authors, categories, genres, publishers |
| 03 | `12_product_db_seed.sql` | product_db | categories, products |
| 04 | `04_staff_db_seed.sql` | staff_db | staff_users, staffs |
| 05 | `05_cart_db_seed.sql` | cart_db | carts, cart_items |
| 06 | `06_order_db_seed.sql` | order_db | discounts, orders, order_items, order_discounts, invoices, coupons |
| 07 | `07_pay_db_seed.sql` | pay_db | payment_methods, payments, transactions, customer_payment_methods |
| 08 | `08_ship_db_seed.sql` | ship_db | shipping_methods, shipping_features, shippings, shipping_addresses, shipping_statuses |
| 09 | `09_manager_db_seed.sql` | manager_db | managers |
| 10 | `10_comment_rate_db_seed.sql` | comment_rate_db | reviews, review_likes |
| 11 | `11_recommender_db_seed.sql` | recommender_db | recommendations, customer_behaviors |

## Cách chạy

### DBeaver (khuyến nghị trên Windows – không cần cài psql)

1. Mở DBeaver, kết nối tới PostgreSQL (user `postgres`).
2. Trong Database Navigator, chọn đúng database (ví dụ `customer_db`).
3. Mở file SQL: **File → Open File** → chọn `01_customer_db_seed.sql`.
4. Chạy script: **Ctrl+Alt+X** (Execute Script) hoặc nút ▶ Execute.
5. Lặp lại với từng DB: `product_db` → mở `12_product_db_seed.sql`, `cart_db` → mở `05_cart_db_seed.sql`, … đến `11_recommender_db_seed.sql`.

**Lưu ý:** Phải chọn đúng database tương ứng với file (ví dụ khi chạy `05_cart_db_seed.sql` thì database đang mở phải là `cart_db`).

---

### psql (khi đã có PostgreSQL client trong PATH)

Trên Windows, `psql` thường **không** nằm trong PATH. Bạn có thể:

- **Cách 1:** Thêm thư mục cài PostgreSQL vào PATH, ví dụ:
  - `C:\Program Files\PostgreSQL\15\bin` (hoặc 14, 16 tùy phiên bản).
  - **Cách thêm:** Tìm "Environment Variables" → System/User → Path → Edit → New → dán đường dẫn `...\PostgreSQL\15\bin` → OK.
- **Cách 2:** Gọi `psql` bằng đường dẫn đầy đủ (đổi 15 theo phiên bản của bạn):

```powershell
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -d customer_db -f "D:\Study\Nam4_Ky2\KTVHTPM\Ecommerce-microservice\scripts\sql\01_customer_db_seed.sql"
```

Sau khi có `psql` trong PATH (hoặc dùng đường dẫn đầy đủ), chạy lần lượt:

```bash
psql -U postgres -d customer_db -f scripts/sql/01_customer_db_seed.sql
psql -U postgres -d catalog_db  -f scripts/sql/02_catalog_db_seed.sql
psql -U postgres -d product_db  -f scripts/sql/12_product_db_seed.sql
# ... tương tự 04 -> 12
```

---

### PowerShell – chạy tất cả (chỉ khi đã có psql)

Nếu **đã thêm PostgreSQL\bin vào PATH** (hoặc bạn đặt đường dẫn trong biến `$PsqlPath`):

```powershell
cd D:\Study\Nam4_Ky2\KTVHTPM\Ecommerce-microservice

# Nếu psql chưa trong PATH, gán đường dẫn đầy đủ (đổi 15 theo phiên bản):
# $PsqlPath = "C:\Program Files\PostgreSQL\15\bin\psql.exe"
# Else: $PsqlPath = "psql"

$PsqlPath = "psql"
$dbs = @('auth_db','user_db','product_db','cart_db','order_db','pay_db','ship_db','recommender_db')
$i = 1
foreach ($db in $dbs) {
  $file = Get-ChildItem "scripts\sql\$($i.ToString('00'))_*_seed.sql" | Select-Object -First 1 -ExpandProperty FullName
  if ($file) { & $PsqlPath -U postgres -d $db -f $file }
  $i++
}
```

Nếu báo lỗi **"psql is not recognized"** → dùng **DBeaver** (phần trên) hoặc thêm `C:\Program Files\PostgreSQL\15\bin` vào PATH rồi chạy lại.

**Script tự tìm psql:** Trong thư mục `scripts/sql/` có file `run_seeds.ps1`. Chạy từ thư mục gốc project:

```powershell
.\scripts\sql\run_seeds.ps1
```

Script sẽ tìm `psql.exe` trong các thư mục cài PostgreSQL (14–16). Nếu không tìm thấy, in hướng dẫn dùng DBeaver.

## Lưu ý

- **Bảng phải đã tồn tại** (đã chạy Django `migrate` hoặc script tạo bảng). Các file này chỉ **INSERT**, không tạo bảng.
- **Password (users, staff_users):** Hash trong SQL là placeholder. Để **đăng nhập** được (customer1, staff1, manager1 / password123), nên chạy `python manage.py seed_mock` trong **customer-service** và **staff-service** sau khi import SQL, hoặc cập nhật cột `password` bằng kết quả từ Django: `from django.contrib.auth.hashers import make_password; make_password('password123')`.
- Mỗi file dùng `TRUNCATE ... RESTART IDENTITY CASCADE` để **xóa dữ liệu cũ** trước khi chèn. Chỉ chạy khi bạn chấp nhận mất dữ liệu hiện tại trong các bảng đó.
