"""
Train NMF từ dữ liệu **thật** của hệ thống — khớp customer_id / book_id trên web:

  - Bảng BehaviorEvent (recommender DB): view, cart, wishlist, …
  - GET order-service `/orders/metrics/` (AllowAny): lịch sử mua theo customer

Chạy (order-service phải reachable; trên Windows dùng localhost + PORT_ORDER):

  python manage.py train_implicit_cf_local

Ghi đè model vào IMPLICIT_CF_DATA_DIR — sau đó restart recommender-ai-service.
"""
from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Sum
from scipy.sparse import csr_matrix

from app.models import BehaviorEvent
from app.services.cf_training_utils import save_nmf_model

# Cùng thang với RecommenderService.action_weights["purchase"]
_PURCHASE_EDGE_WEIGHT = 4.0


def _resolve_order_service_url(cli: str) -> str:
    u = (cli or "").strip()
    if u:
        return u.rstrip("/")
    local = os.environ.get("ORDER_SERVICE_LOCAL_URL", "").strip()
    if local:
        return local.rstrip("/")
    bs = os.environ.get("ORDER_SERVICE_URL", "").strip()
    in_docker = os.path.exists("/.dockerenv")
    if in_docker:
        return (bs or "http://order-service:8000").rstrip("/")
    if bs and "order-service" not in bs:
        return bs.rstrip("/")
    port = os.environ.get("PORT_ORDER", "8007").strip() or "8007"
    return f"http://127.0.0.1:{port}"


def _fetch_order_metrics(base: str) -> list[dict]:
    url = f"{base.rstrip('/')}/orders/metrics/"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []


class Command(BaseCommand):
    help = "Train NMF từ behavior + đơn hàng (customer_id / book_id local)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--order-service-url",
            type=str,
            default="",
            help="URL order-service (mặc định: localhost+PORT_ORDER khi chạy ngoài Docker)",
        )
        parser.add_argument(
            "--no-orders",
            action="store_true",
            help="Chỉ dùng BehaviorEvent, không gọi order-service",
        )
        parser.add_argument(
            "--purchase-weight",
            type=float,
            default=_PURCHASE_EDGE_WEIGHT,
            help="Trọng số cạnh (customer, book) từ đơn hàng",
        )
        parser.add_argument(
            "--factors",
            type=int,
            default=32,
            help="Số latent factors (mặc định 32 — phù hợp dữ liệu nhỏ)",
        )
        parser.add_argument(
            "--max-iter",
            type=int,
            default=200,
            help="max_iter NMF",
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            default="",
            help="Thư mục output (mặc định IMPLICIT_CF_DATA_DIR)",
        )
        parser.add_argument(
            "--min-nnz",
            type=int,
            default=8,
            help="Tối thiểu số cạnh user–book để train (dưới ngưỡng sẽ cảnh báo)",
        )

    def handle(self, *args, **options):
        out_dir = Path(options["output_dir"] or settings.IMPLICIT_CF_DATA_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)

        weights: dict[tuple[int, int], float] = defaultdict(float)

        # 1) Behavior
        q = BehaviorEvent.objects.values("customer_id", "book_id").annotate(
            total=Sum("action_weight")
        )
        for row in q:
            cid = int(row["customer_id"])
            bid = int(row["book_id"])
            weights[(cid, bid)] += float(row["total"] or 0.0)

        n_behavior = len(weights)

        # 2) Orders (metrics)
        if not options["no_orders"]:
            base = _resolve_order_service_url(options.get("order_service_url") or "")
            self.stdout.write(f"Lấy đơn từ: {base}/orders/metrics/")
            try:
                metrics = _fetch_order_metrics(base)
            except requests.RequestException as e:
                self.stderr.write(
                    self.style.WARNING(
                        f"Không lấy được orders/metrics ({e}). Chỉ dùng behavior. "
                        f"Hoặc chạy với --no-orders nếu cố ý."
                    )
                )
                metrics = []
            pw = float(options["purchase_weight"])
            for entry in metrics:
                try:
                    cid = int(entry["customer_id"])
                except (KeyError, TypeError, ValueError):
                    continue
                for raw in set(entry.get("purchase_ids") or []):
                    try:
                        bid = int(raw)
                    except (TypeError, ValueError):
                        continue
                    weights[(cid, bid)] += pw
        else:
            metrics = []
            self.stdout.write("Bỏ qua order-service (--no-orders).")

        if not weights:
            self.stderr.write(
                self.style.ERROR(
                    "Không có dữ liệu (behavior rỗng và không có đơn). "
                    "Hãy tạo vài đơn / gửi behavior từ web rồi chạy lại."
                )
            )
            return

        users = sorted({p[0] for p in weights})
        books = sorted({p[1] for p in weights})
        user_id_to_idx = {str(u): i for i, u in enumerate(users)}
        item_id_to_idx = {b: j for j, b in enumerate(books)}
        idx_to_book_id = list(books)

        row_ind, col_ind, data = [], [], []
        for (u, b), w in weights.items():
            if w <= 0:
                continue
            row_ind.append(user_id_to_idx[str(u)])
            col_ind.append(item_id_to_idx[b])
            data.append(float(w))

        n_users = len(users)
        n_items = len(books)
        nnz = len(data)
        matrix = csr_matrix(
            (np.array(data, dtype=np.float64), (row_ind, col_ind)),
            shape=(n_users, n_items),
        )

        self.stdout.write(
            f"Matrix: {n_users} users × {n_items} items, nnz={nnz} "
            f"(behavior_edges≈{n_behavior}, orders_rows={len(metrics)})"
        )

        min_nnz = int(options["min_nnz"])
        if nnz < min_nnz or n_users < 2 or n_items < 2:
            self.stderr.write(
                self.style.WARNING(
                    f"Dữ liệu mỏng (nnz={nnz}, users={n_users}, items={n_items}). "
                    f"NMF có thể kém ổn định — nên thu thập thêm đơn/hành vi."
                )
            )

        n_comp = save_nmf_model(
            matrix,
            user_id_to_idx,
            idx_to_book_id,
            out_dir,
            extra_meta={
                "source": "local_behavior_and_orders",
                "orders_metrics_rows": len(metrics),
            },
            factors=int(options["factors"]),
            max_iter=int(options["max_iter"]),
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Đã lưu NMF (K={n_comp}) → {out_dir}\n"
                "Gợi ý API dùng đúng customer_id đã có trong dữ liệu trên."
            )
        )
