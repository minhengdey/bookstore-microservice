// ============================================================
// NEO4J KNOWLEDGE GRAPH — VISUALIZATION SCRIPT
// E-Commerce Recommender AI Service
// Schema: User -[PERFORMED]-> Product -[BELONGS_TO]-> Category
//
// HOW TO USE:
//   1. Mở Neo4j Browser tại http://localhost:7474
//   2. Chạy từng SECTION theo thứ tự (copy-paste từng block)
//   3. Hoặc chạy toàn bộ file qua: cypher-shell -f neo4j_visualize_kg.cypher
// ============================================================


// ============================================================
// SECTION 0 — RESET (chỉ chạy khi muốn xóa sạch & rebuild)
// ============================================================
// MATCH (n) DETACH DELETE n;


// ============================================================
// SECTION 1 — LOAD DATA từ CSV (nếu chưa có data)
// File CSV phải nằm trong thư mục import của Neo4j:
//   Neo4j Desktop: <db-folder>/import/data_user500.csv
//   Docker:        /var/lib/neo4j/import/data_user500.csv
// ============================================================

// 1a. Tạo User nodes
LOAD CSV WITH HEADERS FROM 'file:///data_user500.csv' AS row
MERGE (u:User {user_id: row.user_id})
  ON CREATE SET u.created_at = datetime();

// 1b. Tạo Product nodes + Category nodes + BELONGS_TO edge
LOAD CSV WITH HEADERS FROM 'file:///data_user500.csv' AS row
MERGE (p:Product {product_id: row.product_id})
  ON CREATE SET
    p.name     = row.product_name,
    p.category = row.category
MERGE (c:Category {name: row.category})
MERGE (p)-[:BELONGS_TO]->(c);

// 1c. Tạo PERFORMED edges (User → Product) với đầy đủ properties
LOAD CSV WITH HEADERS FROM 'file:///data_user500.csv' AS row
MATCH (u:User    {user_id:    row.user_id})
MATCH (p:Product {product_id: row.product_id})
CREATE (u)-[:PERFORMED {
  action:     row.action,
  timestamp:  row.timestamp,
  device:     row.device,
  session_id: row.session_id,
  persona:    row.persona
}]->(p);


// ============================================================
// SECTION 2 — INDEXES (tăng tốc query)
// ============================================================

CREATE INDEX user_id_idx    IF NOT EXISTS FOR (u:User)     ON (u.user_id);
CREATE INDEX product_id_idx IF NOT EXISTS FOR (p:Product)  ON (p.product_id);
CREATE INDEX category_idx   IF NOT EXISTS FOR (c:Category) ON (c.name);


// ============================================================
// SECTION 3 — OVERVIEW: Toàn bộ graph (giới hạn 300 nodes)
// Dùng để xem tổng quan cấu trúc trong Neo4j Browser
// ============================================================

MATCH (u:User)-[r:PERFORMED]->(p:Product)-[:BELONGS_TO]->(c:Category)
RETURN u, r, p, c
LIMIT 300;


// ============================================================
// SECTION 4 — DEMO: 3 Users mẫu (giống Hình 3.8 trong tài liệu)
// U001, U002, U003 với các actions purchase/view/add_to_cart/wishlist
// ============================================================

MATCH path = (u:User)-[r:PERFORMED]->(p:Product)-[:BELONGS_TO]->(c:Category)
WHERE u.user_id IN ['U001', 'U002', 'U003']
RETURN path;


// ============================================================
// SECTION 5 — ACTION WEIGHT MAP
// Hiển thị trọng số từng action (theo DEFAULT_ACTION_WEIGHTS)
// purchase=5.0, review=2.5, add_to_cart=3.0, wishlist=2.0,
// click=1.5, view=1.0, search=0.4, remove_from_cart=-1.0
// ============================================================

MATCH (u:User)-[r:PERFORMED]->(p:Product)
WITH u.user_id AS user_id,
     p.product_id AS product_id,
     p.name AS product_name,
     r.action AS action,
     CASE r.action
       WHEN 'purchase'         THEN 5.0
       WHEN 'review'           THEN 2.5
       WHEN 'add_to_cart'      THEN 3.0
       WHEN 'wishlist'         THEN 2.0
       WHEN 'click'            THEN 1.5
       WHEN 'view'             THEN 1.0
       WHEN 'search'           THEN 0.4
       WHEN 'remove_from_cart' THEN -1.0
       ELSE 0.0
     END AS action_weight
RETURN user_id, product_id, product_name, action, action_weight
ORDER BY user_id, action_weight DESC
LIMIT 50;


// ============================================================
// SECTION 6 — ANTI-SUPER-NODE DETECTION
// Logic: tính tổng score per product, tìm P95 threshold,
// đánh dấu super-nodes (bestsellers bị loại khỏi gợi ý)
// ============================================================

// 6a. Tính product_score tổng hợp (clip max 5.0 per user per product)
MATCH (u:User)-[r:PERFORMED]->(p:Product)
WITH p,
     u,
     min(
       sum(CASE r.action
         WHEN 'purchase'         THEN 5.0
         WHEN 'review'           THEN 2.5
         WHEN 'add_to_cart'      THEN 3.0
         WHEN 'wishlist'         THEN 2.0
         WHEN 'click'            THEN 1.5
         WHEN 'view'             THEN 1.0
         WHEN 'search'           THEN 0.4
         WHEN 'remove_from_cart' THEN -1.0
         ELSE 0.0
       END),
       5.0                        -- clip max 5.0 per user per product
     ) AS clipped_score
WITH p, sum(clipped_score) AS total_score
RETURN p.product_id   AS product_id,
       p.name         AS product_name,
       p.category     AS category,
       round(total_score, 2) AS total_score
ORDER BY total_score DESC
LIMIT 30;

// 6b. Xác định Super-Nodes (vượt percentile 95)
MATCH (u:User)-[r:PERFORMED]->(p:Product)
WITH p,
     u,
     min(
       sum(CASE r.action
         WHEN 'purchase'         THEN 5.0
         WHEN 'review'           THEN 2.5
         WHEN 'add_to_cart'      THEN 3.0
         WHEN 'wishlist'         THEN 2.0
         WHEN 'click'            THEN 1.5
         WHEN 'view'             THEN 1.0
         WHEN 'search'           THEN 0.4
         WHEN 'remove_from_cart' THEN -1.0
         ELSE 0.0
       END),
       5.0
     ) AS clipped_score
WITH p, sum(clipped_score) AS total_score
WITH collect({product_id: p.product_id, name: p.name, score: total_score}) AS all_products,
     count(p) AS total_count
UNWIND all_products AS prod
WITH prod, total_count,
     all_products,
     toInteger(total_count * 0.95) AS p95_rank
WITH all_products, p95_rank
ORDER BY p95_rank
WITH all_products[p95_rank].score AS p95_threshold, all_products
UNWIND all_products AS prod
WHERE prod.score >= p95_threshold
RETURN prod.product_id AS super_node_product_id,
       prod.name       AS product_name,
       round(prod.score, 2) AS score,
       'EXCLUDED from recommendations' AS status;


// ============================================================
// SECTION 7 — DIVERSIFIED RECOMMENDATIONS (60/30/10 logic)
// Lấy top categories của user, phân bổ 60% primary / 30% secondary / 10% explore
// ============================================================

// 7a. Top categories của từng user (dùng để tính 60/30/10)
MATCH (u:User)-[r:PERFORMED]->(p:Product)-[:BELONGS_TO]->(c:Category)
WITH u.user_id AS user_id,
     c.name AS category,
     sum(CASE r.action
       WHEN 'purchase'    THEN 5.0
       WHEN 'add_to_cart' THEN 3.0
       WHEN 'wishlist'    THEN 2.0
       WHEN 'view'        THEN 1.0
       WHEN 'click'       THEN 1.5
       WHEN 'search'      THEN 0.4
       ELSE 0.0
     END) AS category_score
WITH user_id, collect({category: category, score: category_score}) AS cat_scores
UNWIND cat_scores AS cs
RETURN user_id,
       cs.category AS category,
       round(cs.score, 2) AS score,
       CASE
         WHEN cs.score = head([x IN cat_scores | x.score ORDER BY x.score DESC])
           THEN 'PRIMARY (60%)'
         WHEN cs.score >= head(tail([x IN cat_scores | x.score ORDER BY x.score DESC]))
           THEN 'SECONDARY (30%)'
         ELSE 'EXPLORE (10%)'
       END AS allocation
ORDER BY user_id, score DESC
LIMIT 40;

// 7b. Visualize: User → Category preference graph
MATCH (u:User)-[r:PERFORMED]->(p:Product)-[:BELONGS_TO]->(c:Category)
WITH u, c, count(r) AS interaction_count,
     sum(CASE r.action
       WHEN 'purchase'    THEN 5.0
       WHEN 'add_to_cart' THEN 3.0
       WHEN 'wishlist'    THEN 2.0
       WHEN 'view'        THEN 1.0
       WHEN 'click'       THEN 1.5
       WHEN 'search'      THEN 0.4
       ELSE 0.0
     END) AS pref_score
MERGE (u)-[pref:PREFERS]->(c)
  SET pref.score = round(pref_score, 2),
      pref.interactions = interaction_count
RETURN u, pref, c
LIMIT 100;


// ============================================================
// SECTION 8 — GRAPH STATISTICS (tổng quan số liệu)
// ============================================================

// 8a. Đếm nodes theo loại
MATCH (n)
RETURN labels(n)[0] AS node_type, count(n) AS count
ORDER BY count DESC;

// 8b. Đếm relationships theo loại
MATCH ()-[r]->()
RETURN type(r) AS relationship_type, count(r) AS count
ORDER BY count DESC;

// 8c. Phân bố actions
MATCH ()-[r:PERFORMED]->()
RETURN r.action AS action, count(r) AS count
ORDER BY count DESC;

// 8d. Top 10 products được tương tác nhiều nhất
MATCH (u:User)-[r:PERFORMED]->(p:Product)
RETURN p.product_id   AS product_id,
       p.name         AS product_name,
       p.category     AS category,
       count(r)       AS total_interactions,
       count(DISTINCT u) AS unique_users
ORDER BY total_interactions DESC
LIMIT 10;

// 8e. Top 10 users hoạt động nhất
MATCH (u:User)-[r:PERFORMED]->(p:Product)
RETURN u.user_id          AS user_id,
       count(r)            AS total_actions,
       count(DISTINCT p)   AS unique_products,
       collect(DISTINCT r.action) AS action_types
ORDER BY total_actions DESC
LIMIT 10;


// ============================================================
// SECTION 9 — CO-PURCHASE GRAPH
// Tìm các cặp sản phẩm thường được mua cùng nhau
// (dùng trong hybrid recommender: co_buyer_products logic)
// ============================================================

MATCH (u1:User)-[r1:PERFORMED {action: 'purchase'}]->(p1:Product),
      (u1)-[r2:PERFORMED {action: 'purchase'}]->(p2:Product)
WHERE p1.product_id < p2.product_id
WITH p1, p2, count(DISTINCT u1) AS co_buyers
WHERE co_buyers >= 2
MERGE (p1)-[co:CO_PURCHASED]->(p2)
  SET co.co_buyers = co_buyers
RETURN p1.name AS product_1,
       p2.name AS product_2,
       co_buyers
ORDER BY co_buyers DESC
LIMIT 20;


// ============================================================
// SECTION 10 — FULL GRAPH VISUALIZATION (Neo4j Browser)
// Chạy query này trong Neo4j Browser để xem toàn bộ graph
// với màu sắc phân biệt theo node type
// ============================================================

MATCH (u:User)-[r:PERFORMED]->(p:Product)-[b:BELONGS_TO]->(c:Category)
RETURN u, r, p, b, c
LIMIT 200;

// Tip: Trong Neo4j Browser, vào panel bên trái:
//   - User nodes     → đặt màu #6c63ff (tím)
//   - Product nodes  → đặt màu #ff6b6b (đỏ)
//   - Category nodes → đặt màu #00d9a3 (xanh lá)
//   - PERFORMED edge → hiển thị property "action"
//   - BELONGS_TO edge → ẩn label để gọn hơn
