# AI Service E2E Checklist

## 1) Bootstrap
- Ensure `.env` has `GRAPH_KB_PATH`, `GNN_ARTIFACT_DIR`, `AI_BOOTSTRAP_KB`.
- Start stack: `docker compose up -d recommender-ai-service api-gateway book-service order-service`.
- Run migrations if needed: `python manage.py migrate`.

## 2) Product Seed (>=10)
- Seed catalog and books:
  - `python manage.py seed_mock --clear` in `book-service`.
- Verify `/books/` returns at least 10 items.

## 3) Behavior + Graph
- Send events: `POST /api/recommender/events/` with `customer_id`, `book_id`, `action`.
- Verify graph stats: `GET /api/recommender/graph` has `nodes_count > 0` and `edges_count > 0`.

## 4) Train AI
- Run: `python manage.py train_ai`.
- Verify artifacts:
  - `app/services/ai_engine/checkpoints/full_pipeline.pt`
  - `app/services/ai_engine/checkpoints/gnn/gnn_recommender.pt`
  - `app/services/ai_engine/checkpoints/gnn/gnn_meta.json`

## 5) Recommendation API
- Call: `GET /recommendations/<customer_id>/?limit=10`
- Verify response includes:
  - `recommended_book_ids`
  - `recommendations[].score`
  - `recommendations[].explanation`

## 6) Chat RAG
- Call: `POST /api/recommender/chat` with `query` and optional `user_profile`.
- Verify response includes `sources` with `score` and `graph_popularity`.

## 7) Web Verification
- Login as customer on gateway.
- Open `/recommendations/`.
- Click books + add to cart, refresh recommendations, verify changes.
