"""
Tạo file JSON map book_id (dataset Kaggle / goodbooks) → book_id local (book-service).

Cần file books.csv từ cùng bộ goodbooks-10k (tải trên Kaggle cùng ratings.csv).

  python manage.py build_book_id_map --kaggle-books "D:\\path\\to\\books.csv"

Mặc định lấy sách từ BOOK_SERVICE_URL (book-service đang chạy). Ghi ra data/book_id_map.json

Sau đó train lại NMF kèm map:

  python manage.py train_implicit_cf --ratings .../ratings.csv --book-map data/book_id_map.json
"""
import csv
import json
import os
import re
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand


def _norm_isbn(s: str) -> str:
    return re.sub(r"\D", "", (s or "").strip())


def _norm_title(s: str) -> str:
    return " ".join((s or "").lower().split())


def _load_kaggle_books(path: Path):
    """book_id -> {isbn, title}"""
    by_id = {}
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("books.csv rỗng")
        fn = {k.strip().lower(): k for k in reader.fieldnames}
        bid_col = fn.get("book_id") or fn.get("id")
        if not bid_col:
            raise ValueError("Cần cột book_id hoặc id trong books.csv")
        isbn_col = fn.get("isbn")
        isbn13_col = fn.get("isbn13")
        title_col = fn.get("title") or fn.get("original_title")
        for row in reader:
            try:
                bid = int(str(row[bid_col]).strip())
            except (ValueError, KeyError):
                continue
            isbn = ""
            if isbn_col and isbn_col in row:
                isbn = _norm_isbn(row[isbn_col])
            if not isbn and isbn13_col and isbn13_col in row:
                isbn = _norm_isbn(row[isbn13_col])
            title = ""
            if title_col and title_col in row:
                title = _norm_title(row[title_col])
            by_id[bid] = {"isbn": isbn, "title": title}
    return by_id


def _resolve_book_service_url(cli_url: str) -> str:
    """
    Trên máy host, hostname `book-service` không resolve (chỉ có trong Docker network).
    Nếu không truyền --book-service-url: dùng localhost + PORT_BOOK khi cần.
    """
    u = (cli_url or "").strip()
    if u:
        return u.rstrip("/")
    local = os.environ.get("BOOK_SERVICE_LOCAL_URL", "").strip()
    if local:
        return local.rstrip("/")
    bs = os.environ.get("BOOK_SERVICE_URL", "").strip()
    in_docker = os.path.exists("/.dockerenv")
    if in_docker:
        return (bs or "http://book-service:8000").rstrip("/")
    if bs and "book-service" not in bs:
        return bs.rstrip("/")
    port = os.environ.get("PORT_BOOK", "8002").strip() or "8002"
    return f"http://127.0.0.1:{port}"


def _fetch_all_books(base_url: str, page_size: int = 200) -> list[dict]:
    out = []
    page = 1
    while True:
        url = f"{base_url.rstrip('/')}/books/"
        r = requests.get(url, params={"page": page, "page_size": page_size}, timeout=60)
        r.raise_for_status()
        data = r.json()
        chunk = data.get("results", data) if isinstance(data, dict) else data
        if not isinstance(chunk, list):
            break
        out.extend(chunk)
        total_pages = data.get("total_pages") if isinstance(data, dict) else None
        if not chunk or (total_pages and page >= total_pages):
            break
        page += 1
        if page > 5000:
            break
    return out


class Command(BaseCommand):
    help = "Build book_id_map.json: dataset book_id → local book id (ISBN / title)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--kaggle-books",
            type=str,
            required=True,
            help="Đường dẫn books.csv (goodbooks-10k)",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="",
            help="File JSON output (mặc định: data/book_id_map.json)",
        )
        parser.add_argument(
            "--book-service-url",
            type=str,
            default="",
            help="URL book-service (mặc định: localhost+PORT_BOOK nếu chạy ngoài Docker)",
        )
        parser.add_argument(
            "--match-title",
            action="store_true",
            help="Nếu không khớp ISBN, thử khớp title (chính xác sau chuẩn hóa)",
        )

    def handle(self, *args, **options):
        kaggle_path = Path(options["kaggle_books"]).expanduser().resolve()
        if not kaggle_path.is_file():
            self.stderr.write(self.style.ERROR(f"Không tìm thấy: {kaggle_path}"))
            return

        out_path = Path(options["output"] or (settings.BASE_DIR / "data" / "book_id_map.json"))
        out_path.parent.mkdir(parents=True, exist_ok=True)

        base = _resolve_book_service_url(options.get("book_service_url") or "")
        self.stdout.write(f"Đang đọc Kaggle books: {kaggle_path}")
        kaggle = _load_kaggle_books(kaggle_path)
        self.stdout.write(f"  → {len(kaggle)} dòng sách (theo book_id)")

        self.stdout.write(f"Đang gọi book-service: {base}")
        try:
            local_books = _fetch_all_books(base)
        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f"Không gọi được book-service: {e}"))
            return

        by_isbn: dict[str, int] = {}
        by_title: dict[str, int] = {}
        for b in local_books:
            bid = int(b["id"])
            isbn = _norm_isbn(b.get("isbn") or "")
            if isbn and isbn not in by_isbn:
                by_isbn[isbn] = bid
            t = _norm_title(b.get("title") or "")
            if t and t not in by_title:
                by_title[t] = bid

        mapping: dict[str, int] = {}
        matched_isbn = 0
        matched_title = 0
        for ds_id, info in kaggle.items():
            local_id = None
            if info["isbn"] and info["isbn"] in by_isbn:
                local_id = by_isbn[info["isbn"]]
                matched_isbn += 1
            elif options["match_title"] and info["title"] and info["title"] in by_title:
                local_id = by_title[info["title"]]
                matched_title += 1
            if local_id is not None:
                mapping[str(ds_id)] = local_id

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)

        self.stdout.write(
            self.style.SUCCESS(
                f"Đã ghi {len(mapping)} cặp map → {out_path}\n"
                f"  Khớp ISBN: {matched_isbn}, khớp title: {matched_title}, "
                f"sách local: {len(local_books)}"
            )
        )
        self.stdout.write(
            "Bước tiếp: python manage.py train_implicit_cf --ratings ... --book-map "
            f'"{out_path}"'
        )
