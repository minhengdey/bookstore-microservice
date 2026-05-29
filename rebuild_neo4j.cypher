MATCH (n) DETACH DELETE n;

LOAD CSV WITH HEADERS FROM 'file:///data_user500.csv' AS row
MERGE (u:User {user_id: row.user_id})
MERGE (p:Product {product_id: row.product_id})
  ON CREATE SET p.name = row.product_name, p.category = row.category
MERGE (c:Category {name: row.category})
MERGE (a:Action {name: row.action})
MERGE (p)-[:BELONGS_TO]->(c);

LOAD CSV WITH HEADERS FROM 'file:///data_user500.csv' AS row
MATCH (u:User {user_id: row.user_id})
MATCH (p:Product {product_id: row.product_id})
CREATE (u)-[r:PERFORMED {action: row.action, timestamp: row.timestamp, device: row.device}]->(p);
