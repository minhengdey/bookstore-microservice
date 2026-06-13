# -*- coding: utf-8 -*-
"""Chapter 4 section 4.14 — detailed UI/system results (4.14.1–4.14.11)."""

def _screen(title, intro, purpose, ui, data_flow, backend, ai, result, comment):
    return f"""### {title}

#### 1. Giới thiệu chức năng

{intro}

#### 2. Mục đích

{purpose}

#### 3. Mô tả giao diện

{ui}

#### 4. Mô tả luồng dữ liệu

{data_flow}

#### 5. Mô tả xử lý backend

{backend}

#### 6. Mô tả xử lý AI

{ai}

#### 7. Kết quả đạt được

{result}

#### 8. Nhận xét

{comment}

---

"""


SEC_414 = r"""## 4.14 THỂ HIỆN KẾT QUẢ HỆ THỐNG

Phần này mô tả **từng màn hình storefront** đã triển khai trong `api-gateway/templates/`. Mỗi mục phân tích đầy đủ: giao diện nhìn thấy gì, phía sau gọi service nào, database nào thay đổi, AI có tham gia hay không.

> **Ghi chú hình ảnh:** Khi chèn screenshot vào báo cáo Word/PDF, đặt tên file theo mục (vd. `4.14.1_home.png`). Phần chữ bên dưới đã đủ 300–500 từ/mục — ảnh minh họa bổ sung trực quan, không thay thế phân tích kỹ thuật.

""" + _screen(
    "4.14.1 Trang chủ",
    "Trang chủ (`GET /`, view `home`, template `home.html`) là điểm vào chính của storefront. Với **khách vãng lai (guest)**, hệ thống hiển thị sản phẩm mới nhất theo phân trang 12 item/trang, kèm carousel flash sale và lưới danh mục. Với **khách hàng đã đăng nhập (customer)**, danh sách sản phẩm chính được **sắp xếp theo điểm gợi ý AI** thay vì thứ tự cố định — đây là điểm khác biệt quan trọng so với guest.",
    "Mục đích trang chủ: (1) giới thiệu catalog, (2) kích thích mua flash sale, (3) cá nhân hóa trải nghiệm bằng recommendation cho user đã có behavior, (4) điều hướng nhanh tới category và chi tiết sản phẩm.",
    "Giao diện gồm header navigation (logo, sản phẩm, giỏ, đơn hàng, profile), banner flash sale cuộn ngang (4 sản phẩm/slide), block danh mục (chunk 6 category/icon), lưới product card (ảnh, tên, giá đã format VND, badge giảm giá nếu flash sale). Customer thấy nhãn gợi ý cá nhân; guest thấy 'Sản phẩm mới'. Cuối trang có nút 'Xem thêm' kích hoạt infinite scroll JavaScript.",
    "Luồng dữ liệu bắt đầu từ browser `GET /` → NGINX → `api-gateway.home()`. View đọc `request.session['user']` để xác định role. Song song (ThreadPoolExecutor): gọi `product-service/products/?flash_sale=true`, `product-service/categories/`. Nếu customer: thêm nhánh `recommender-ai-service/recommendations/{entity_id}/` → nhận `recommended_product_ids` → `product-service` hydrate từng id → `_fmt_product()` format tiền. Response HTML render context dict vào `home.html`. Infinite scroll: customer gọi `GET /api/home/products/?page=N`; guest gọi `GET /api/guest/products/?page=N` — JSON trả về card đã rút gọn.",
    "`home()` trong `views.py` (~dòng 742–834) là orchestrator. Không query DB trực tiếp — mọi persistence qua REST. Cache ngắn 10s cho product list (`cache_ttl=10`) giảm latency. `_customer_recommendation_products_page()` fallback sang `sort_by=newest` nếu recommender trả danh sách rỗng (log warning). Staff/manager vào `/` thấy dashboard số liệu đơn giản (tổng SP, đơn) — không dùng AI.",
    "AI tham gia **chỉ với customer đã login**: `RecommenderService.recommend(customer_id)` kết hợp behavior matrix (`recommender_db`), co-purchase từ `order-service/internal/recommender-orders/`, category affinity. Kết quả là thứ tự product card trên trang chủ. Flash sale và category **không** qua AI — lấy trực tiếp product-service. Guest không gửi event recommender khi chỉ xem trang chủ.",
    "Trang chủ hoạt động end-to-end: load < 3s trong môi trường Docker local (phụ thuộc cold start). Customer nhận danh sách khác guest nếu đã có lịch sử xem/mua. Infinite scroll append card không reload trang.",
    "Điểm mạnh: tích hợp AI không chặn render — có fallback. Điểm cần cải thiện: lần đầu recommender load model có thể chậm; nên warm-up container trước demo.",
) + _screen(
    "4.14.2 Trang đăng ký",
    "Trang đăng ký (`GET/POST /register/`, `register_view`, template `register.html`) cho phép tạo tài khoản khách hàng mới. Form gồm username, email, password, phone. Submit POST không qua JavaScript framework — form HTML truyền thống Django.",
    "Mục đích: onboarding user, tạo identity trong auth-service và profile customer trong user-service (xử lý nội bộ auth), tự động đăng nhập sau đăng ký thành công để giảm friction.",
    "Giao diện: form căn giữa, label tiếng Việt, hiển thị `error` dict từ serializer nếu validation fail (email trùng, password yếu...). Thành công redirect sang trang chủ — user thấy header đã có tên đăng nhập.",
    "POST `/register/` → gateway ghép payload `role: customer` → `POST auth-service/auth/register/`. Auth service validate `RegisterSerializer`, hash password, tạo user, liên kết customer entity_id. Response 201 chứa `access`, `refresh`, `user` → gateway lưu session Django (`access_token`, `user`) → redirect `home`. Không gọi AI ở bước đăng ký.",
    "`register_view` (~dòng 673–696): try/except `RequestException` hiển thị 'Auth service unavailable' nếu container auth chưa sẵn sàng. Session-based auth — browser chỉ giữ `sessionid` cookie, JWT nằm server-side session. DB ghi: `auth_db` users + audit; user-service có thể được gọi async hoặc trong register flow của AuthService (xem `authentication/services.py`).",
    "Chưa có AI. Sau đăng ký, lần đầu vào home user ở trạng thái **cold start** — recommender dùng trending/category fallback cho đến khi có behavior.",
    "Đăng ký thành công tạo session và chuyển home trong một flow. Lỗi validation hiển thị rõ từng field.",
    "Thiếu trong code so với spec tài liệu màn hình: OTP email, OAuth Google — **không tìm thấy trong source code**.",
) + _screen(
    "4.14.3 Trang đăng nhập",
    "Trang đăng nhập (`GET/POST /login/`, `login_view`, `login.html`) hỗ trợ ba persona: customer, staff, admin — chọn qua `login_type` query/post. Cùng form username/password nhưng auth-service kiểm tra role tương ứng.",
    "Mục đích: xác thực, phân luồng sau login — customer → home storefront; staff → `/staff/dashboard/`; admin/manager → `/admin/dashboard/`.",
    "Giao diện: ô username, password, selector loại đăng nhập, link đăng ký. Lỗi hiển thị banner đỏ ('Login failed', rate limit...).",
    "POST → `auth-service/auth/login/` với `{username, password, role: login_type}`. 200 → session lưu token + user object. Redirect theo role trong `roles` array. GET `/login/` chỉ render form — không backend call.",
    "auth-service áp dụng rate limit IP (`_rate_limit_login` — Redis/cache), ghi `AuthAudit` mỗi lần thử. NGINX có thể dùng `auth/introspect` cho route bảo vệ — storefront session vẫn do gateway quản lý. JWT refresh có endpoint riêng nhưng gateway chủ yếu dùng session lâu dài trong demo.",
    "Không AI trực tiếp. Sau login customer, session `entity_id` dùng cho mọi API cart, recommendation, behavior tracking.",
    "Phân quyền đúng role đã triển khai. Staff không lẫn vào storefront admin nếu chọn đúng login_type.",
    "Chưa có: quên mật khẩu, 2FA — không có trong repo.",
) + _screen(
    "4.14.4 Danh sách sản phẩm",
    "Trang danh sách (`GET /products/`, `product_list`, `product_list.html`) hiển thị catalog có lọc: category, khoảng giá, sắp xếp. Staff/admin có thể POST thêm sản phẩm từ form trên cùng trang (không phải customer).",
    "Mục đích: duyệt catalog có điều kiện, điểm vào chi tiết sản phẩm, thu thập behavior `view` khi click vào card (tracking ở product_detail).",
    "Giao diện: sidebar/filter bar category, input min/max price, select sort (newest, price...), grid 14 sản phẩm/trang, phân trang. Product card link tới `/products/{id}/`.",
    "GET: parallel fetch `product-service/products/` với query params từ `request.GET` + `categories/`. Gateway `_fmt_product` cho mỗi row. POST (staff): `_post product-service/products/` với name, sku, price, category_id, image_url. Customer POST bị 403.",
    "`product_list` (~910+): `_list_query_params` chuẩn hóa pagination. Cache category 300s. Không gọi recommender cho sort — thứ tự theo product-service (trừ khi mở rộng sau này). DB: `product_db` bảng Product, Category.",
    "Khi user click sang chi tiết, `product_detail` gọi `track_behavior(..., 'view')` — đây là điểm AI bắt đầu ghi nhận sở thích từ danh sách.",
    "Lọc và phân trang hoạt động ổn định. Staff thêm SP trực tiếp từ UI trong môi trường demo.",
    "Có thể bổ sung sort theo recommendation score trong tương lai — hiện chưa có trong code.",
) + _screen(
    "4.14.5 Chi tiết sản phẩm",
    "Trang chi tiết (`GET /products/{id}/`, `product_detail`, `product_detail.html`) hiển thị đầy đủ thông tin một SKU: ảnh, mô tả, giá (kèm flash sale), tồn kho, variant nếu có, nút thêm giỏ, wishlist, đánh giá.",
    "Mục đích: quyết định mua, thêm cart, ghi behavior view/click, hiển thị review từ interaction-service.",
    "Giao diện: layout 2 cột (ảnh | thông tin), nút 'Thêm vào giỏ', 'Yêu thích', tab mô tả/đánh giá, form review nếu customer đã mua và đơn eligible.",
    "GET: `product-service/products/{id}/`, reviews `interaction-service/api/v1/interactions/reviews/?product_id=`, wishlist status nếu login. POST add cart: `cart-service/carts/{customer_id}/items/`. Mỗi view gọi `track_behavior(request, customer_id, product_id, 'view')` khi load.",
    "`product_detail` hydrate variant, kiểm tra flash sale từ product payload. Review POST gọi interaction-service, sau đó `track_behavior(..., 'review')`. Permission: chỉ customer sở hữu đơn delivered mới review (`_REVIEW_ELIGIBLE_ORDER_STATUSES`).",
    "Behavior event gửi recommender (`POST events/`) và interaction bus — cập nhật matrix CF và Neo4j async qua consumer. Ảnh hưởng gợi ý lần sau trên home.",
    "Chi tiết SP là nguồn behavior quan trọng nhất cho AI. Luồng thêm giỏ → cart-service `cart_db` insert item.",
    "Variant và flash sale hiển thị đúng effective_price. Review gắn chặt trạng thái đơn — tránh spam.",
) + _screen(
    "4.14.6 Giỏ hàng",
    "Trang giỏ (`GET /cart/{customer_id}/`, `view_cart`, `cart.html`) liệt kê item, số lượng, đơn giá, tổng tiền, nút cập nhật/xóa, nút 'Thanh toán' sang checkout.",
    "Mục đích: tập hợp intent mua trước checkout, cho phép sửa quantity, xóa item, tracking `add_to_cart`/`remove_from_cart`.",
    "Giao diện: bảng line items (ảnh thumbnail, tên, đơn giá, input quantity, subtotal), tổng cộng footer, CTA checkout. Giỏ trống hiển thị message hướng dẫn mua sắm.",
    "GET `cart-service/carts/{customer_id}/` → items[]. POST update: PUT `carts/{id}/items/{item_id}/`. DELETE item: DELETE item endpoint. Gateway có thể enrich tên SP từ product-service. `track_behavior` khi thêm/xóa từ product_detail hoặc cart action.",
    "Cart service lưu `cart_db` — mỗi customer một cart document + line items. Gateway `customer_can_only_own` đảm bảo không xem giỏ người khác. Sau checkout thành công cart bị DELETE toàn bộ.",
    "Mỗi add_to_cart tăng trọng số recommendation cho product_id đó trong recommender_db — ảnh hưởng hybrid score.",
    "Giỏ đồng bộ realtime qua REST. Checkout chỉ enable khi có item và user đã login đúng customer_id.",
    "Session cart API (`/cart/` không customer_id) tồn tại trong cart-service nhưng storefront dùng customer cart — nhất quán với đăng nhập bắt buộc.",
) + _screen(
    "4.14.7 Thanh toán (Checkout + Payment)",
    "Checkout (`GET/POST /cart/{customer_id}/checkout/`, `checkout.html`) xác nhận địa chỉ, phí ship, voucher, ghi chú. Sau POST thành công redirect `order_pay` — chọn PT thanh toán (`order_pay.html`, mock gateway).",
    "Mục đích: hoàn tất đặt hàng legacy flow, tính phí vận chuyển động, áp khuyến mãi, chuyển sang payment và trigger async shipping.",
    "Checkout UI: chọn địa chỉ có sẵn hoặc link thêm mới, dropdown shipping method, hiển thị phí ship AJAX (`checkout_shipping_fees_api`), ô voucher, textarea notes, bảng tóm tắt đơn. Payment UI: radio payment methods, COD vs mock VNPay/MoMo redirect mock page.",
    "POST checkout: validate → `user-service` address → `shipping-service/api/shipping/calculate-fee/` → build `order_items` hydrate product → `POST order-service/orders/` → `DELETE cart` → redirect pay. POST pay COD: `POST payment-service/payments/` → `track_order_purchases` → order_list. Mock: render gateway → callback GET → payment POST.",
    "`checkout` (~1376–1501) validation tầng gateway trước khi gọi order. Order service gọi `product-service/internal/reserve-stock/`. Payment publish RabbitMQ → shipping-consumer tạo vận đơn. DB: order_db, payment_db, product inventory transaction.",
    "`track_order_purchases` gửi `purchase` event từng line item — **tín hiệu mạnh nhất** cho recommender. Cập nhật co-purchase graph Neo4j qua recommender-consumer.",
    "Đặt hàng COD end-to-end hoạt động trong Docker. Mock payment mô phỏng redirect gateway thật.",
    "Chưa dùng SAGA checkout v2 trên UI. VNPay/MoMo là mock — không gọi API thật.",
) + _screen(
    "4.14.8 Quản lý đơn hàng",
    "Trang đơn hàng customer: `GET /orders/` (`order_list`), chi tiết `/orders/{id}/`, tracking `/orders/{id}/tracking/`. Staff có `/staff/orders/` cập nhật trạng thái bulk.",
    "Mục đích: theo dõi lifecycle đơn sau mua — chờ thanh toán, đang giao, đã giao; cho phép trả hàng, thanh toán lại nếu pending.",
    "Giao diện: bảng đơn (mã, ngày, tổng tiền, trạng thái tiếng Việt qua `ORDER_STATUS_VI`), filter, link chi tiết. Chi tiết: line items, địa chỉ ship snapshot, timeline tracking từ shipping-service.",
    "GET orders: `order-service/orders/` với JWT — customer chỉ thấy đơn mình (filter phía service hoặc gateway). Detail: `orders/{id}/` + `shipping-service/api/shippings/order/{id}/`. AJAX poll `orders/api/status/` cho badge realtime.",
    "`_fmt_order` enrich format tiền và địa chỉ. Staff `staff_order_update_status` PUT order status — trigger notification có thể qua outbox. Return request: `POST orders/{id}/return/`.",
    "Đơn completed/delivered mở khóa review — gián tiếp ảnh hưởng AI qua review behavior. Purchase đã track lúc thanh toán.",
    "Khách theo dõi được đơn sau checkout. Trạng thái dịch tiếng Việt rõ ràng.",
    "Notification email/push có service nhưng storefront chủ yếu hiển thị in-app.",
) + _screen(
    "4.14.9 AI Chatbot",
    "Chatbot widget (JS) nhúng trên mọi trang storefront. User gõ câu hỏi → `POST /ai/chat/` → hiển thị bubble trả lời + product cards gợi ý.",
    "Mục đích: tư vấn sản phẩm tự nhiên tiếng Việt, giảm tải support, demo RAG + LLM tích hợp commerce.",
    "Giao diện: icon tròn góc phải, panel chat, input text, danh sách tin nhắn user/bot, card sản phẩm (ảnh, tên, giá) click sang product_detail.",
    "Browser JSON POST same-origin → `ai_chat_proxy` → `recommender-ai-service/api/recommender/chat-ktmp` body `{message, user_id, history, recent_behaviors}`. Response `{answer, products, intent}` render client-side. history[] giữ trong JS memory/sessionStorage.",
    "Proxy retry 3 lần, timeout 90s. Không lưu chat vào PostgreSQL storefront — stateless mỗi request (history do client gửi lại). Groq API key chỉ ở recommender container env.",
    "Pipeline: intent_router → HybridProductRetriever (KB pickle) → graph context → Groq sinh answer. `products` trong response là kết quả retrieval + rerank, không phải random.",
    "Chatbot trả lời được câu hỏi về danh mục, giá, gợi ý SP liên quan. Lỗi 503/504 có message thân thiện khi model đang load.",
    "Phụ thuộc `GROQ_API_KEY` — thiếu key thì chat degrade. Nên seed catalog index trước demo.",
) + _screen(
    "4.14.10 AI Recommendation",
    "Hiển thị ở trang chủ customer, trang `/recommendations/`, và admin `/admin/recommendation/`. Core: danh sách SP sắp theo điểm hybrid.",
    "Mục đích: cá nhân hóa catalog, tăng CTR/conversion, demo pipeline ML + graph + behavior.",
    "**Dữ liệu đầu vào:** toàn bộ behavior events (view, cart, wishlist, purchase, review) trong `recommender_db`; orders qua internal API; catalog metadata; Neo4j edges (async). **Luồng xử lý:** `GET recommendations/{id}/` → RecommenderService.recommend() → weighted hybrid score → top ids → gateway hydrate product → render. **Kết quả:** user thấy SP 'dành cho bạn' khác guest; admin thấy strategy string và scores.",
    "Product card giống catalog nhưng thứ tự theo score. Trang recommendations đầy đủ hơn home page_size. Infinite scroll `/api/home/products/` giữ thứ tự recommendation khi page>1.",
    "Gateway `_recommendation_order_ids` → recommender REST. Fallback newest nếu empty. Parallel không block flash sale section.",
    "5 chiến lược hybrid (CF, co-occurrence, co-purchase, category, fallback). Next-action prediction có API riêng — có thể hiển thị tooltip 'Bạn có thể thích' (tùy template).",
    "Khách có lịch sử mua nhận gợi ý khớp category đã mua. Cold start dùng trending — không crash.",
    "Độ chính xác phụ thuộc lượng behavior seed — chạy `seed_mock` và `sync_*_behaviors` trước đánh giá.",
) + _screen(
    "4.14.11 GraphRAG Query",
    "GraphRAG thể hiện qua: (1) chatbot context có nguồn graph, (2) recommendation pipeline Neo4j candidates, (3) admin/debug graph stats nếu bật endpoint. Không có trang UI riêng 'Graph Explorer' trong storefront — chủ yếu quan sát qua kết quả gợi ý và chat.",
    "Mục đích: mở rộng ngữ cảnh retrieval bằng quan hệ user–product–category, không chỉ text similarity.",
    "Trong chat: user hỏi 'tôi hay mua đồ công nghệ, gợi ý tương tự' — bot trả lời kèm SP cùng category graph. Recommendation: user mua laptop → graph walk gợi ý phụ kiện cùng category.",
    "Query text → RAG retrieve → `GraphRepository.get_context` đọc `graph_kb.json` cạnh INTERACTED, BELONGS_TO. Song song Neo4j Cypher trong `recommendation_pipeline` cho candidate IDs. Event mới → `recommender-consumer` cập nhật graph.",
    "graph_kb.json persist trên volume recommender. Neo4j bolt driver trong AI service settings. Không expose Cypher cho end-user — chỉ nội bộ service.",
    "Graph context string đưa vào prompt LLM field `context_used` trong response API — debug được nguồn. Popularity từ graph edge weight ảnh hưởng rerank.",
    "Quan hệ đồ thị phản ánh behavior thật sau vài phiên mua sắm demo. Category expansion giúp gợi ý đa dạng hơn pure CF.",
    "Hai graph store (JSON + Neo4j) cần giải thích khi bảo vệ — tránh nhầm một nguồn duy nhất.",
)
