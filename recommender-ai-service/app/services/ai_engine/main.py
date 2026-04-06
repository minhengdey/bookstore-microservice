"""
main.py
-------
Entry-point CLI để xây dựng KB, train model, và test chatbot.

Run:
    python main.py --kb-only        # Chỉ build KB + vector store
    python main.py --train          # Train 3-stage DL model
    python main.py --chat           # Interactive chatbot (skip training)
    python main.py --demo           # Demo queries (skip training)
    python main.py                  # Build KB + train + interactive chat

v2 — Phù hợp với train.py v2, vector_store.py v2, rag_pipeline.py v2.
"""

import os
import sys
import argparse

# ── Path setup ──────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Build Knowledge Base + Vector Store
# ══════════════════════════════════════════════════════════════════════════════

def setup_kb(force_rebuild: bool = False):
    """
    Bước 1: Tạo knowledge_base.json
    Bước 2: Build HNSW vector store (text_hnsw.index + meta.json)
    """
    from build_kb_bookstore import build_knowledge_base
    from vector_store import build_vector_store

    kb_json        = os.path.join(ROOT, "kb", "knowledge_base.json")
    text_index     = os.path.join(ROOT, "kb", "text_hnsw.index")
    dl_index       = os.path.join(ROOT, "kb", "dl_hnsw.index")
    meta_path      = os.path.join(ROOT, "kb", "meta.json")

    # ── Build KB JSON ─────────────────────────────────────────────────────────
    if force_rebuild or not os.path.exists(kb_json):
        print("\n[1/2] Building knowledge base …")
        build_knowledge_base(output_path=kb_json)
    else:
        print(f"[1/2] KB already exists at {kb_json} — skipping.")

    # ── Build HNSW vector store ───────────────────────────────────────────────
    if force_rebuild or not os.path.exists(meta_path):
        print("\n[2/2] Building HNSW vector store …")
        build_vector_store(
            kb_path        = kb_json,
            text_index_path = text_index,
            dl_index_path   = dl_index,
            meta_path       = meta_path,
        )
    else:
        print(f"[2/2] Vector store already exists — skipping. "
              f"(Dùng --rebuild-kb để force rebuild)")


# ══════════════════════════════════════════════════════════════════════════════
# 2. Train DL Model (3-stage)
# ══════════════════════════════════════════════════════════════════════════════

def run_training(
    recall_epochs: int  = 10,
    ranking_epochs: int = 15,
    dqn_steps: int      = 2000,
    batch_size: int     = 32,
    n_train: int        = 3000,
    n_val: int          = 600,
):
    """
    Train Customer Behavior Pipeline — 3 stages:
      Stage 1: Two-Tower Recall (InfoNCE loss)
      Stage 2: Deep Interest Network Ranking (multi-task)
      Stage 3: Dueling DQN Re-ranking (experience replay)

    Checkpoint lưu tại: checkpoints/full_pipeline.pt
    """
    from train import train

    print("\n" + "═" * 55)
    print("  Bắt đầu train 3-stage DL model  ")
    print("═" * 55)

    checkpoint_dir = os.path.join(ROOT, "checkpoints")

    model = train(
        recall_epochs  = recall_epochs,
        ranking_epochs = ranking_epochs,
        dqn_steps      = dqn_steps,
        batch_size     = batch_size,
        save_dir       = checkpoint_dir,
        n_train        = n_train,
        n_val          = n_val,
    )
    return model


# ══════════════════════════════════════════════════════════════════════════════
# 3. Test RAG Pipeline
# ══════════════════════════════════════════════════════════════════════════════

def run_demo():
    """Demo với 3 câu hỏi mẫu (non-interactive)."""
    from rag_pipeline import RAGPipeline

    text_index = os.path.join(ROOT, "kb", "text_hnsw.index")
    meta_path  = os.path.join(ROOT, "kb", "meta.json")

    print("\n─── Demo RAG Pipeline v2 ───")
    pipeline = RAGPipeline(top_k=4)

    profile = {
        "age"      : 28,
        "gender"   : "female",
        "location" : "Hà Nội",
        "interests": ["tiểu thuyết", "self-help", "kinh doanh"],
    }

    questions = [
        "Mình muốn tìm tiểu thuyết trinh thám dễ đọc.",
        "Có sách self-help nào thực tế cho người mới đi làm không?",
        "Gợi ý giúp mình vài sách kinh doanh cho startup.",
    ]

    for q in questions:
        print(f"\n{'─'*50}")
        resp = pipeline.chat(q, user_profile=profile)
        print(f"👤 {q}")
        print(f"\n🤖 {resp.answer[:500]}")
        print(f"   📊 Confidence : {resp.confidence:.0%}")
        print(f"   📎 Citations  : {resp.citations}")


def run_interactive():
    """Interactive chat loop (multi-turn)."""
    from rag_pipeline import RAGPipeline
    import os as _os

    pipeline = RAGPipeline(top_k=5)

    print("\nNhập profile (Enter để bỏ qua):")
    age   = input("  Tuổi: ").strip()
    loc   = input("  Địa điểm: ").strip()
    inter = input("  Sở thích (cách nhau dấu phẩy): ").strip()

    profile: dict = {}
    if age:
        try:
            profile["age"] = int(age)
        except ValueError:
            pass
    if loc:
        profile["location"] = loc
    if inter:
        profile["interests"] = [x.strip() for x in inter.split(",")]

    print(f"\nProfile: {profile or 'Không có'}")
    print("'reset' để xoá lịch sử | Ctrl+C để thoát\n" + "═" * 50)

    while True:
        try:
            query = input("\n👤 Bạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTạm biệt!")
            break

        if not query:
            continue
        if query.lower() == "reset":
            pipeline.reset()
            print("[Đã xoá lịch sử]")
            continue

        resp = pipeline.chat(query, user_profile=profile or None)
        print(f"\n🤖 Tư vấn viên:\n{resp.answer}")
        if resp.sources:
            print(f"\n   📎 Nguồn: {' | '.join(s.service_name for s in resp.sources[:3])}")
        print(f"   📊 Confidence: {resp.confidence:.0%}")


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Recommender AI Service — Main CLI"
    )
    parser.add_argument("--kb-only",    action="store_true",
                        help="Chỉ build KB + vector store rồi thoát")
    parser.add_argument("--train",      action="store_true",
                        help="Train DL model (3 stages)")
    parser.add_argument("--chat",       action="store_true",
                        help="Interactive chat (bỏ qua training)")
    parser.add_argument("--demo",       action="store_true",
                        help="Demo queries (không cần input)")
    parser.add_argument("--rebuild-kb", action="store_true",
                        help="Force rebuild KB + vector store")

    # Training hyperparams
    parser.add_argument("--recall-epochs",  type=int, default=10)
    parser.add_argument("--ranking-epochs", type=int, default=15)
    parser.add_argument("--dqn-steps",      type=int, default=2000)
    parser.add_argument("--batch",          type=int, default=32)
    parser.add_argument("--n-train",        type=int, default=3000)

    args = parser.parse_args()

    # Luôn đảm bảo KB tồn tại
    setup_kb(force_rebuild=args.rebuild_kb)

    if args.kb_only:
        print("\n✅ KB setup xong. Thoát.")
        sys.exit(0)

    if args.train:
        run_training(
            recall_epochs  = args.recall_epochs,
            ranking_epochs = args.ranking_epochs,
            dqn_steps      = args.dqn_steps,
            batch_size     = args.batch,
            n_train        = args.n_train,
        )

    if args.demo:
        run_demo()
    elif args.chat or not args.train:
        run_interactive()
