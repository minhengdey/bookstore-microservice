"""
ai_singleton.py
---------------
Singleton quản lý RAGPipeline và DL model (CustomerBehaviorPipeline).
Được import bởi Django views để tránh reinitialise model mỗi request.

v2 — phù hợp với rag_pipeline.py v2, model_behavior.py v2, vector_store.py v2
"""

import os
import sys
import torch
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────────
AI_ENGINE_DIR = Path(__file__).resolve().parent / "ai_engine"
sys.path.insert(0, str(AI_ENGINE_DIR))

# Import từ v2 modules
from rag_pipeline import RAGPipeline, HybridRetriever
from model_behavior import CustomerBehaviorPipeline, ModelConfig

# ── Paths (v2 vector store) ─────────────────────────────────────────────────
TEXT_INDEX_PATH = str(AI_ENGINE_DIR / "kb" / "text_hnsw.index")
META_PATH       = str(AI_ENGINE_DIR / "kb" / "meta.json")
DL_INDEX_PATH   = str(AI_ENGINE_DIR / "kb" / "dl_hnsw.index")
CHECKPOINT_PATH = str(AI_ENGINE_DIR / "checkpoints" / "full_pipeline.pt")


class AIModelSingleton:
    """
    Thread-safe singleton cho RAGPipeline + DL model.

    Sử dụng:
        pipeline = AIModelSingleton.get_pipeline()
        result   = pipeline.chat(query, user_profile=...)
    """

    _pipeline:             RAGPipeline = None
    _dl_model:             CustomerBehaviorPipeline = None
    _dl_model_last_mtime:  float = 0.0
    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # ── RAG Pipeline ────────────────────────────────────────────────────────

    @classmethod
    def get_pipeline(cls) -> RAGPipeline:
        """
        Trả về RAGPipeline singleton.
        HybridRetriever được tạo trong RAGPipeline constructor nếu không truyền vào.
        """
        if cls._pipeline is None:
            print("[AI Singleton] Initializing RAG Pipeline …")
            try:
                # Thử load với HNSW index đã build sẵn
                retriever = HybridRetriever(
                    text_index=TEXT_INDEX_PATH,
                    dl_index=DL_INDEX_PATH,
                    meta_path=META_PATH,
                )
                cls._pipeline = RAGPipeline(retriever=retriever, top_k=5)
                print("[AI Singleton] RAG Pipeline ready (với vector store đã build).")
            except Exception as e:
                print(f"[AI Singleton] Không load được vector store ({e}). "
                      f"Dùng retriever mặc định (mock fallback).")
                # RAGPipeline sẽ tự tạo HybridRetriever — trả về empty nếu không có index
                cls._pipeline = RAGPipeline(top_k=5)

        return cls._pipeline

    # ── DL Model (CustomerBehaviorPipeline) ────────────────────────────────

    @classmethod
    def get_dl_model(cls) -> CustomerBehaviorPipeline | None:
        """
        Load (hoặc hot-reload) DL model từ checkpoint.
        Trả về None nếu chưa train.
        """
        if not os.path.exists(CHECKPOINT_PATH):
            return None

        mtime = os.path.getmtime(CHECKPOINT_PATH)
        if cls._dl_model is None or mtime > cls._dl_model_last_mtime:
            print(f"[AI Singleton] Loading DL model từ {CHECKPOINT_PATH} …")
            try:
                ckpt = torch.load(CHECKPOINT_PATH, map_location=cls._device,
                                  weights_only=False)
                cfg = ModelConfig()
                # Restore hyperparams từ checkpoint
                for k, v in ckpt.get("cfg", {}).items():
                    if hasattr(cfg, k) and not callable(getattr(cfg, k)):
                        setattr(cfg, k, v)

                model = CustomerBehaviorPipeline(cfg).to(cls._device)
                model.load_state_dict(ckpt["model_state"])
                model.eval()

                cls._dl_model            = model
                cls._dl_model_last_mtime = mtime
                print("[AI Singleton] DL model loaded.")
            except Exception as e:
                print(f"[AI Singleton] Load DL model failed: {e}")

        return cls._dl_model

    # ── DL Score Prediction ─────────────────────────────────────────────────

    @classmethod
    def predict_dl_scores(cls, user_profile: dict) -> dict:
        """
        Dự đoán recommendation scores cho tất cả services dựa trên user_profile.

        Returns:
            { "SVC001": 0.82, "SVC002": 0.61, … }  hoặc {} nếu model chưa có.
        """
        model = cls.get_dl_model()
        if model is None or not user_profile:
            return {}

        try:
            cfg = model.cfg
            B   = 1

            # ── User features ───────────────────────────────────────────────
            user_id_val = int(user_profile.get("user_id", 1))
            user_ids = torch.tensor([user_id_val], dtype=torch.long,
                                    device=cls._device)

            age_norm = float(user_profile.get("age", 30)) / 100.0
            ages     = torch.tensor([[age_norm]], dtype=torch.float,
                                    device=cls._device)

            gender_val = 1.0 if str(user_profile.get("gender", "")).lower() in \
                         ("male", "nam", "m") else 0.0
            genders = torch.tensor([[gender_val]], dtype=torch.float,
                                   device=cls._device)

            loc_id = int(user_profile.get("location_id", 1)) % (cfg.num_locations)
            location_ids = torch.tensor([max(1, loc_id)], dtype=torch.long,
                                        device=cls._device)

            # ── Purchase / Browsing history ─────────────────────────────────
            raw_p = [int(x) % cfg.num_items for x in
                     user_profile.get("purchase_ids", [1]) if x]
            raw_b = [int(x) % cfg.num_items for x in
                     user_profile.get("browsing_ids",  raw_p or [1]) if x]

            raw_p = raw_p or [1]
            raw_b = raw_b or [1]

            T_p = len(raw_p)
            T_b = len(raw_b)

            purchase_ids  = torch.tensor([raw_p], dtype=torch.long,
                                         device=cls._device)
            purchase_lens = torch.tensor([T_p],  dtype=torch.long,
                                         device=cls._device)
            browsing_ids  = torch.tensor([raw_b], dtype=torch.long,
                                         device=cls._device)
            browsing_lens = torch.tensor([T_b],  dtype=torch.long,
                                         device=cls._device)

            # ── Inference ───────────────────────────────────────────────────
            with torch.no_grad():
                # Stage 1: lấy user embedding từ UserTower
                user_emb = model.get_user_embedding(
                    user_ids, ages, genders, location_ids,
                    purchase_ids, purchase_lens,
                    browsing_ids,  browsing_lens,
                )

                # Stage 2: DIN ranking — score tất cả services
                # Sử dụng một target giả để lấy service head output
                context_feats = torch.zeros(B, 8, device=cls._device)
                all_svc_scores = []

                for svc_idx in range(1, cfg.num_services + 1):
                    target_ids = torch.tensor([svc_idx], dtype=torch.long,
                                              device=cls._device)
                    _, _, _, svc_scores_raw = model.forward_ranking(
                        user_emb, target_ids,
                        purchase_ids, purchase_lens,
                        browsing_ids,  browsing_lens,
                        context_feats,
                    )
                    # svc_scores_raw: (1, num_services) → lấy score cho target svc
                    all_svc_scores.append(
                        float(svc_scores_raw[0, svc_idx - 1].cpu())
                    )

            # ── Map về SVC IDs ───────────────────────────────────────────────
            # Hỗ trợ cả ID kiểu cũ (SVCxxx) và kiểu bookstore (BOOKxxx).
            score_map = {}
            for i, score in enumerate(all_svc_scores, start=1):
                score_map[f"SVC{i:03d}"] = score
                score_map[f"BOOK{i:03d}"] = score
            return score_map

        except Exception as e:
            print(f"[AI Singleton] predict_dl_scores error: {e}")
            return {}
