"""
Gắn book_id_map.json vào meta.json của model đã train (không train lại NMF).

  python manage.py apply_book_id_map --map data/book_id_map.json

Hữu ích khi đã train xong rồi mới tạo map từ build_book_id_map.
"""
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cập nhật dataset_book_id_to_local_book_id trong data/implicit_cf/meta.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--map",
            dest="map_path",
            type=str,
            required=True,
            help="File JSON map (dataset book_id → local id)",
        )
        parser.add_argument(
            "--data-dir",
            type=str,
            default="",
            help="Thư mục chứa meta.json (mặc định: IMPLICIT_CF_DATA_DIR)",
        )

    def handle(self, *args, **options):
        mpath = Path(options["map_path"]).expanduser().resolve()
        if not mpath.is_file():
            self.stderr.write(self.style.ERROR(f"Không tìm thấy: {mpath}"))
            return

        data_dir = Path(options["data_dir"] or settings.IMPLICIT_CF_DATA_DIR)
        meta_path = data_dir / "meta.json"
        if not meta_path.is_file():
            self.stderr.write(self.style.ERROR(f"Chưa có model: {meta_path}"))
            return

        with open(mpath, encoding="utf-8") as f:
            book_map = json.load(f)
        book_map = {str(k): int(v) for k, v in book_map.items()}

        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)

        meta["dataset_book_id_to_local_book_id"] = book_map

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        self.stdout.write(
            self.style.SUCCESS(f"Đã gắn {len(book_map)} map vào {meta_path}")
        )
