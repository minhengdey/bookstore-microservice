"""
Huấn luyện matrix factorization (NMF) từ CSV (rating / implicit feedback).

Ví dụ goodbooks-10k: tải ratings.csv từ Kaggle, đặt vào thư mục rồi chạy:

  python manage.py train_implicit_cf --ratings /path/to/ratings.csv

Map book_id dataset → book_id local (book-service), nếu khác nhau:

  python manage.py train_implicit_cf --ratings ratings.csv --book-map book_id_map.json

**Cho web hiện tại (customer_id + book_id local):** dùng

  python manage.py train_implicit_cf_local

Artifacts ghi vào IMPLICIT_CF_DATA_DIR (mặc định: data/implicit_cf/).
"""
import csv
import json
from pathlib import Path

import numpy as np
from django.conf import settings
from django.core.management.base import BaseCommand
from scipy.sparse import csr_matrix

from app.services.cf_training_utils import save_nmf_model


def _read_ratings(path: Path, user_col: str, book_col: str, rating_col: str | None, min_rating: float):
    rows = []
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV rỗng hoặc không có header")
        fn = {k.strip().lower(): k for k in reader.fieldnames}
        uc = fn.get(user_col.lower())
        bc = fn.get(book_col.lower())
        rc = fn.get(rating_col.lower()) if rating_col else None
        if not uc or not bc:
            raise ValueError(
                f"Không tìm thấy cột: {user_col}, {book_col}. "
                f"Có: {list(reader.fieldnames)}"
            )
        for line in reader:
            try:
                u = int(line[uc].strip())
                b = int(line[bc].strip())
            except (ValueError, KeyError):
                continue
            if rc and rc in line:
                try:
                    r = float(line[rc].strip())
                except ValueError:
                    r = 1.0
                if r < min_rating:
                    continue
            else:
                r = 1.0
            rows.append((u, b, r))
    if not rows:
        raise ValueError("Không đọc được dòng hợp lệ nào từ CSV")
    return rows


class Command(BaseCommand):
    help = "Train NMF matrix factorization từ CSV (Kaggle / goodbooks ratings)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ratings",
            type=str,
            required=True,
            help="Đường dẫn ratings.csv (user_id, book_id, rating)",
        )
        parser.add_argument(
            "--user-col",
            type=str,
            default="user_id",
            help="Tên cột user (mặc định: user_id)",
        )
        parser.add_argument(
            "--book-col",
            type=str,
            default="book_id",
            help="Tên cột book (mặc định: book_id)",
        )
        parser.add_argument(
            "--rating-col",
            type=str,
            default="rating",
            help="Tên cột rating; dùng '' nếu không có (cần --implicit-only)",
        )
        parser.add_argument(
            "--implicit-only",
            action="store_true",
            help="Bỏ qua cột rating, mọi tương tác weight=1",
        )
        parser.add_argument(
            "--min-rating",
            type=float,
            default=0.0,
            help="Chỉ giữ rating >= giá trị này (mặc định: 0 = giữ hết)",
        )
        parser.add_argument(
            "--factors",
            type=int,
            default=64,
            help="Số latent factors (NMF components)",
        )
        parser.add_argument(
            "--max-iter",
            type=int,
            default=200,
            help="max_iter cho NMF",
        )
        parser.add_argument(
            "--alpha",
            type=float,
            default=0.25,
            help="Trọng số confidence = 1 + alpha * rating",
        )
        parser.add_argument(
            "--book-map",
            type=str,
            default="",
            help="JSON map dataset_book_id → local_book_id (tùy chọn)",
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            default="",
            help="Thư mục ghi model (mặc định: IMPLICIT_CF_DATA_DIR)",
        )

    def handle(self, *args, **options):
        ratings_path = Path(options["ratings"]).expanduser().resolve()
        if not ratings_path.is_file():
            self.stderr.write(self.style.ERROR(f"Không tìm thấy file: {ratings_path}"))
            return

        out_dir = Path(options["output_dir"] or settings.IMPLICIT_CF_DATA_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)

        if options.get("implicit_only"):
            rating_col = None
        else:
            rating_col = (options["rating_col"] or "").strip() or None
        rows = _read_ratings(
            ratings_path,
            options["user_col"],
            options["book_col"],
            rating_col,
            options["min_rating"],
        )

        users = sorted({r[0] for r in rows})
        books = sorted({r[1] for r in rows})
        user_id_to_idx = {str(u): i for i, u in enumerate(users)}
        item_id_to_idx = {b: j for j, b in enumerate(books)}
        idx_to_book_id = list(books)

        alpha = float(options["alpha"])
        row_ind, col_ind, data = [], [], []
        for u, b, r in rows:
            w = 1.0 + alpha * float(r)
            row_ind.append(user_id_to_idx[str(u)])
            col_ind.append(item_id_to_idx[b])
            data.append(w)

        n_users = len(users)
        n_items = len(books)
        matrix = csr_matrix(
            (np.array(data, dtype=np.float64), (row_ind, col_ind)),
            shape=(n_users, n_items),
        )

        self.stdout.write(
            f"Matrix: {n_users} users × {n_items} items, nnz={matrix.nnz}"
        )

        book_map: dict = {}
        bm_path = (options["book_map"] or "").strip()
        if bm_path:
            p = Path(bm_path).expanduser().resolve()
            if p.is_file():
                with open(p, encoding="utf-8") as f:
                    raw = json.load(f)
                book_map = {str(k): int(v) for k, v in raw.items()}
                self.stdout.write(f"Đã load book map: {len(book_map)} entries")
            else:
                self.stdout.write(self.style.WARNING(f"Không tìm thấy --book-map: {p}"))

        n_comp = save_nmf_model(
            matrix,
            user_id_to_idx,
            idx_to_book_id,
            out_dir,
            extra_meta={
                "source_ratings": str(ratings_path),
                "dataset_book_id_to_local_book_id": book_map,
            },
            factors=int(options["factors"]),
            max_iter=int(options["max_iter"]),
        )

        self.stdout.write(
            self.style.SUCCESS(f"Đã lưu NMF (K={n_comp}) → {out_dir}")
        )
