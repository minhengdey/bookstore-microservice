"""
build_kb_bookstore.py
---------------------
Bookstore-focused knowledge base builder for RAG.
"""

import json
import os
from pathlib import Path
import requests

_THIS_DIR = Path(__file__).resolve().parent
DEFAULT_KB_PATH = str(_THIS_DIR / "kb" / "knowledge_base.json")


BOOK_CATALOGUE = [
    {
        "service_id": "BOOK001",
        "service_name": "Nha Gia Kim",
        "category": "Tieu thuyet",
        "description": "Tieu thuyet kinh dien ve hanh trinh theo duoi uoc mo.",
        "target_age_range": "15-60",
        "price_range": "109000",
        "tags": ["tieu-thuyet", "truyen-cam-hung", "best-seller"],
    },
    {
        "service_id": "BOOK002",
        "service_name": "Dac Nhan Tam",
        "category": "Ky nang song",
        "description": "Sach kinh dien ve giao tiep, ung xu va xay dung moi quan he.",
        "target_age_range": "16-65",
        "price_range": "98000",
        "tags": ["self-help", "giao-tiep", "ky-nang-mem"],
    },
    {
        "service_id": "BOOK003",
        "service_name": "Tu Duy Nhanh Va Cham",
        "category": "Tam ly hoc",
        "description": "Giai thich cach con nguoi ra quyet dinh qua hai he tu duy.",
        "target_age_range": "18-65",
        "price_range": "189000",
        "tags": ["tam-ly", "tu-duy", "hanh-vi"],
    },
    {
        "service_id": "BOOK004",
        "service_name": "Clean Code",
        "category": "Cong nghe",
        "description": "Huong dan viet code sach, de bao tri va thuc hanh tot.",
        "target_age_range": "18-45",
        "price_range": "349000",
        "tags": ["lap-trinh", "software-engineering", "coding"],
    },
    {
        "service_id": "BOOK005",
        "service_name": "De Men Phieu Luu Ky",
        "category": "Thieu nhi",
        "description": "Tac pham thieu nhi noi tieng, phu hop hoc sinh.",
        "target_age_range": "8-14",
        "price_range": "65000",
        "tags": ["thieu-nhi", "van-hoc-viet", "kinh-dien"],
    },
    {
        "service_id": "BOOK006",
        "service_name": "Sherlock Holmes Toan Tap",
        "category": "Trinh tham",
        "description": "Tuyen tap cac vu an noi tieng cua tham tu Sherlock Holmes.",
        "target_age_range": "15-50",
        "price_range": "229000",
        "tags": ["trinh-tham", "mystery", "co-dien"],
    },
    {
        "service_id": "BOOK007",
        "service_name": "Atomic Habits",
        "category": "Phat trien ban than",
        "description": "Phuong phap xay dung thoi quen tot bang thay doi nho.",
        "target_age_range": "16-60",
        "price_range": "185000",
        "tags": ["habit", "self-help", "nang-suat"],
    },
    {
        "service_id": "BOOK008",
        "service_name": "Muon Kiep Nhan Sinh",
        "category": "Tam linh",
        "description": "Tac pham suy ngam ve nhan sinh va hanh trinh noi tam.",
        "target_age_range": "18-65",
        "price_range": "168000",
        "tags": ["tam-linh", "nhan-sinh", "best-seller"],
    },
    {
        "service_id": "BOOK009",
        "service_name": "Cha Giau Cha Ngheo",
        "category": "Tai chinh ca nhan",
        "description": "Nhap mon tu duy tai chinh ca nhan cho nguoi moi bat dau.",
        "target_age_range": "16-55",
        "price_range": "119000",
        "tags": ["tai-chinh", "dau-tu", "self-help"],
    },
    {
        "service_id": "BOOK010",
        "service_name": "Sapiens Luoc Su Loai Nguoi",
        "category": "Lich su",
        "description": "Khai quat lich su loai nguoi tu thoi tien su den hien dai.",
        "target_age_range": "18-65",
        "price_range": "249000",
        "tags": ["lich-su", "khoa-hoc", "phi-hu-cau"],
    },
]


def _price_bucket(price: float) -> str:
    if price <= 0:
        return "N/A"
    if price < 100000:
        return "duoi-100k"
    if price < 200000:
        return "100k-200k"
    if price < 300000:
        return "200k-300k"
    return "tren-300k"


def _normalize_book_item(book: dict) -> dict:
    book_id = book.get("id")
    title = (book.get("title") or "").strip() or f"Book {book_id}"
    description = (book.get("description") or "").strip() or "Chua co mo ta."
    sale_price = float(book.get("sale_price") or 0)
    list_price = float(book.get("list_price") or 0)
    final_price = sale_price if sale_price > 0 else list_price

    publication_year = book.get("publication_year")
    page_count = book.get("page_count")
    stock = book.get("stock")
    status = (book.get("status") or "").strip().lower() or "active"
    category_ids = book.get("category_ids") or []
    genre_ids = book.get("genre_ids") or []

    tags = [
        "book-service",
        f"status-{status}",
        _price_bucket(final_price),
    ]
    if publication_year:
        tags.append(f"year-{publication_year}")
    if page_count:
        tags.append("day-sach" if int(page_count) > 250 else "mong")
    if isinstance(category_ids, list) and category_ids:
        tags.append(f"category-{category_ids[0]}")
    if isinstance(genre_ids, list) and genre_ids:
        tags.append(f"genre-{genre_ids[0]}")

    return {
        "service_id": f"BOOK{int(book_id):03d}" if book_id is not None else f"BOOK-{title[:12]}",
        "service_name": title,
        "category": f"category_{category_ids[0]}" if category_ids else "Sach",
        "description": description,
        "target_age_range": "N/A",
        "price_range": str(int(final_price)) if final_price > 0 else "N/A",
        "tags": tags,
        "stock": stock,
    }


def fetch_books_from_service() -> list:
    """
    Fetch danh sách sách từ book-service.
    Hỗ trợ cả chạy trong Docker network và chạy local.
    """
    base_urls = [
        os.environ.get("BOOK_SERVICE_URL", "").strip(),
        "http://book-service:8000",
        "http://localhost:8002",
    ]
    base_urls = [u.rstrip("/") for u in base_urls if u]

    last_error = None
    for base in base_urls:
        try:
            books = []
            page = 1
            while True:
                resp = requests.get(
                    f"{base}/books/",
                    params={"page": page, "page_size": 200},
                    timeout=15,
                )
                resp.raise_for_status()
                payload = resp.json()

                if isinstance(payload, list):
                    books.extend(payload)
                    break

                page_items = payload.get("results", [])
                books.extend(page_items)
                if not payload.get("next_page"):
                    break
                page += 1

            if books:
                print(f"Fetched {len(books)} books from {base}/books/")
                return books
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"Khong the fetch du lieu tu book-service: {last_error}")


def format_book_document(item: dict) -> str:
    tags = ", ".join(item.get("tags", []))
    return (
        f"Book ID: {item['service_id']}\n"
        f"Title: {item['service_name']}\n"
        f"Category: {item['category']}\n"
        f"Description: {item['description']}\n"
        f"Target Age Range: {item.get('target_age_range', 'N/A')}\n"
        f"Price: {item.get('price_range', 'N/A')} VND\n"
        f"Tags: {tags}"
    )


def build_knowledge_base(catalogue=None, output_path: str = None) -> list:
    if output_path is None:
        output_path = DEFAULT_KB_PATH
    if catalogue is None:
        try:
            raw_books = fetch_books_from_service()
            catalogue = [_normalize_book_item(b) for b in raw_books]
        except Exception as e:
            print(f"[WARN] {e} -> fallback sang BOOK_CATALOGUE local.")
            catalogue = BOOK_CATALOGUE

    kb = []
    for item in catalogue:
        record = dict(item)
        record["document"] = format_book_document(item)
        kb.append(record)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print(f"Knowledge base built: {len(kb)} books -> {output_path}")
    return kb


if __name__ == "__main__":
    build_knowledge_base()
