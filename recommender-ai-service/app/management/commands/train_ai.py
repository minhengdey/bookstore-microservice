from django.core.management.base import BaseCommand
import sys
from pathlib import Path

# Add ai_engine to path
AI_ENGINE_DIR = Path(__file__).resolve().parent.parent.parent / "services" / "ai_engine"
sys.path.insert(0, str(AI_ENGINE_DIR))

from train import train

class Command(BaseCommand):
    help = 'Chạy luồng huấn luyện Deep Learning Model bằng data thực tế.'

    def handle(self, *args, **options):
        self.stdout.write("Bắt đầu tiến trình Training AI Model...")
        try:
            # API train.py v2 dùng recall_epochs / ranking_epochs / dqn_steps
            train(
                recall_epochs=5,
                ranking_epochs=8,
                dqn_steps=500,
                batch_size=32,
                save_dir=str(AI_ENGINE_DIR / "checkpoints"),
            )
            self.stdout.write(self.style.SUCCESS("Đã train và lưu Model thành công!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Quá trình Training thất bại: {e}"))
