"""
Ensure offline recommender artifacts exist (matrix CF from live behavior/orders).
"""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Train implicit CF model if artifacts are missing or stale."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Retrain even if artifacts already exist",
        )
        parser.add_argument(
            "--min-nnz",
            type=int,
            default=4,
            help="Minimum edges required to train (default: 4)",
        )

    def handle(self, *args, **options):
        data_dir = Path(settings.IMPLICIT_CF_DATA_DIR)
        meta_path = data_dir / "meta.json"
        factors_path = data_dir / "factors.npz"

        if not options["force"] and meta_path.is_file() and factors_path.is_file():
            self.stdout.write(self.style.SUCCESS(f"CF model already present at {data_dir}"))
            return

        self.stdout.write("Training matrix CF from behavior + orders...")
        call_command(
            "train_implicit_cf_local",
            min_nnz=int(options["min_nnz"]),
        )
