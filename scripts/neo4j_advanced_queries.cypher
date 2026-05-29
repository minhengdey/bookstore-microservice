// ============================================================================
// Advanced Neo4j Queries for E-Commerce Recommendation (Handling Super Nodes)
// ============================================================================

// 1. CHUẨN HOÁ VÀ TÍNH TRỌNG SỐ (WEIGHT) CHO HÀNH VI
// Chạy đoạn này để cập nhật/tạo thêm trường weight cho các cạnh
MATCH (u:User)-[r:PERFORMED]->(p:Product)
SET r.weight = CASE r.action
    WHEN 'purchase' THEN 5.0
    WHEN 'add_to_cart' THEN 3.0
    WHEN 'wishlist' THEN 2.0
    WHEN 'review' THEN 2.0
    WHEN 'click' THEN 1.0
    WHEN 'view' THEN 1.0
    WHEN 'search' THEN 0.5
    WHEN 'remove_from_cart' THEN -1.0
    ELSE 1.0
END;

// 2. QUERY: TÌM SẢN PHẨM PHỔ BIẾN (LOẠI TRỪ SUPER NODE)
// Thay vì lấy tất cả, bỏ qua các sản phẩm có hơn 500 tương tác (Super Nodes)
MATCH (u:User)-[r:PERFORMED]->(p:Product)
WHERE size((p)<-[:PERFORMED]-()) < 500
WITH p, sum(r.weight) as total_score
ORDER BY total_score DESC
LIMIT 10
RETURN p.product_id, p.name, total_score;

// 3. QUERY: GỢI Ý CỘNG TÁC (COLLABORATIVE FILTERING) TRÁNH SUPER NODE
// "Người mua sản phẩm bạn mua cũng mua sản phẩm nào?"
MATCH (target:User {user_id: 'U001'})-[:PERFORMED {action: 'purchase'}]->(p:Product)<-[:PERFORMED {action: 'purchase'}]-(other:User)
MATCH (other)-[:PERFORMED {action: 'purchase'}]->(rec:Product)
WHERE NOT (target)-[:PERFORMED]->(rec)
  // Lọc bớt các sản phẩm "ai cũng mua" (Super Nodes)
  AND size((rec)<-[:PERFORMED]-()) < 500
RETURN rec.product_id, rec.name, count(DISTINCT other) AS frequency
ORDER BY frequency DESC
LIMIT 5;

// 4. (TÙY CHỌN) ALGORITHM: TÍNH NODE SIMILARITY (YÊU CẦU CÀI ĐẶT GDS PLUGIN)
// Tính toán độ tương đồng giữa các user dựa trên tập hợp sách đã mua,
// cắt giảm sự ảnh hưởng của các "Super Node" bằng thuật toán đồ thị.
/*
CALL gds.nodeSimilarity.stream({
  nodeProjection: ['User', 'Product'],
  relationshipProjection: 'PERFORMED'
})
YIELD node1, node2, similarity
RETURN gds.util.asNode(node1).user_id AS User1, 
       gds.util.asNode(node2).user_id AS User2, similarity
ORDER BY similarity DESC LIMIT 10;
*/
