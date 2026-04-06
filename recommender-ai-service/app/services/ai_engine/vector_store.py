"""
vector_store.py  (v2 — Production-grade)
-----------------------------------------
Nâng cấp theo báo cáo kỹ thuật:

1. HNSW (Hierarchical Navigable Small World) index
   → Tìm kiếm ANN với O(log N) thay vì O(N) brute-force
   → SLA < 100ms dù hàng triệu SKU

2. Incremental Updates
   → Thêm vector mới mà không rebuild toàn bộ index
   → Phù hợp với real-time catalog updates

3. INT8 Quantization
   → Giảm memory footprint ~75%
   → Tương tự TensorRT/ONNX Runtime INT8 trong báo cáo

4. Dual-Tower Integration
   → Dùng DL model embedding thay vì chỉ Sentence-Transformers
   → Kết hợp cả semantic + behavioral signals

5. Multi-index (Semantic + Collaborative)
   → Index 1: text embeddings (Sentence-Transformers)
   → Index 2: DL behavioral embeddings (UserTower output)
   → Hybrid score = α × text_sim + (1-α) × behavioral_sim
"""

import os
import json
import struct
import sys
import numpy as np
from typing import Optional, List, Tuple
from pathlib import Path

try:
    import faiss
    FAISS_OK = True
except ImportError:
    FAISS_OK = False
    print("[WARN] faiss not installed — using numpy fallback (slower)")

try:
    from sentence_transformers import SentenceTransformer
    ST_OK = True
except ImportError:
    ST_OK = False
    print("[WARN] sentence-transformers not installed — using random embeddings")


# ───────────────────────────────────────────────
# Constants — absolute paths relative to this file
# ───────────────────────────────────────────────
_THIS_DIR   = Path(__file__).resolve().parent
KB_DIR      = _THIS_DIR / "kb"

KB_JSON     = str(KB_DIR / "knowledge_base.json")
TEXT_INDEX  = str(KB_DIR / "text_hnsw.index")
DL_INDEX    = str(KB_DIR / "dl_hnsw.index")
META_PATH   = str(KB_DIR / "meta.json")
EMBED_MODEL = "all-MiniLM-L6-v2"   # 384-dim, fast, high quality
TEXT_DIM    = 384
DL_DIM      = 64                    # matches user_tower_dims[-1]

# HNSW params (cân bằng tốc độ / recall)
HNSW_M      = 32     # số edges mỗi node — cao hơn = recall tốt hơn, RAM nhiều hơn
HNSW_EF_C   = 200    # efConstruction — chất lượng index khi build
HNSW_EF_S   = 64     # efSearch — tốc độ / recall tradeoff khi query


# ═══════════════════════════════════════════════
# 1. Encoder
# ═══════════════════════════════════════════════

class MultiModalEncoder:
    """
    Encode service documents và queries.

    Text encoder : Sentence-Transformers (semantic)
    DL encoder   : Neural model (behavioral — tích hợp sau khi train)
    """

    def __init__(self, model_name: str = EMBED_MODEL, dl_model=None):
        self.dl_model = dl_model   # optional: trained CustomerBehaviorPipeline

        if ST_OK:
            print(f"Loading text encoder: {model_name} …")
            self.text_model = SentenceTransformer(model_name)
            self.text_dim   = self.text_model.get_sentence_embedding_dimension()
        else:
            self.text_model = None
            self.text_dim   = TEXT_DIM

    def encode_text(self, texts: List[str], batch_size: int = 32,
                    show_progress: bool = True) -> np.ndarray:
        """Encode text → (N, text_dim) float32, L2-normalized."""
        if self.text_model:
            vecs = self.text_model.encode(
                texts, batch_size=batch_size,
                show_progress_bar=show_progress,
                normalize_embeddings=True,
            )
            return vecs.astype(np.float32)
        else:
            # Deterministic random fallback (reproducible by hash)
            vecs = np.array([
                self._hash_embed(t, self.text_dim) for t in texts
            ], dtype=np.float32)
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            return vecs / (norms + 1e-9)

    def encode_query(self, query: str,
                     user_embedding: Optional[np.ndarray] = None) -> dict:
        """
        Encode một query thành dict vectors để hybrid search.

        Args:
            query          : text query
            user_embedding : (DL_DIM,) optional user vector từ DL model
        Returns:
            {"text": ndarray(1, D_t), "dl": ndarray(1, D_dl) or None}
        """
        text_vec = self.encode_text([query], show_progress=False)   # (1, D_t)
        dl_vec   = None
        if user_embedding is not None:
            dl_vec = user_embedding.reshape(1, -1).astype(np.float32)
            norms  = np.linalg.norm(dl_vec, axis=1, keepdims=True)
            dl_vec = dl_vec / (norms + 1e-9)
        return {"text": text_vec, "dl": dl_vec}

    @staticmethod
    def _hash_embed(text: str, dim: int) -> np.ndarray:
        """Deterministic pseudo-embedding từ text hash (fallback)."""
        seed = hash(text) % (2**31)
        rng  = np.random.RandomState(seed)
        v    = rng.randn(dim).astype(np.float32)
        return v / (np.linalg.norm(v) + 1e-9)


# ═══════════════════════════════════════════════
# 2. HNSW Index Wrapper
# ═══════════════════════════════════════════════

class HNSWIndex:
    """
    FAISS HNSW index với O(log N) ANN search.

    Tại sao HNSW vs flat?
    - Flat: O(N) → không scale được với millions of SKUs
    - HNSW: O(log N) → <100ms SLA với 10M+ vectors
    - Trade-off: build time lâu hơn, RAM nhiều hơn → chấp nhận được

    Tương ứng với Milvus (dùng HNSW core) trong tech stack Shopee.
    """

    def __init__(self, dim: int, metric: str = "cosine",
                 m: int = HNSW_M, ef_c: int = HNSW_EF_C):
        self.dim    = dim
        self.metric = metric
        self._build_index(dim, metric, m, ef_c)
        self.metadata: List[dict] = []

    def _build_index(self, dim, metric, m, ef_c):
        if not FAISS_OK:
            self._index = None
            self._vecs  = None    # numpy fallback
            return

        if metric == "cosine":
            # L2 normalize trước → inner product == cosine
            self._index = faiss.IndexHNSWFlat(dim, m, faiss.METRIC_INNER_PRODUCT)
        else:
            self._index = faiss.IndexHNSWFlat(dim, m, faiss.METRIC_L2)

        self._index.hnsw.efConstruction = ef_c
        self._index.hnsw.efSearch       = HNSW_EF_S

    def add(self, vectors: np.ndarray, meta: List[dict]):
        """Add vectors + metadata (incremental — không cần rebuild)."""
        assert len(vectors) == len(meta)
        vectors = vectors.astype(np.float32)
        # L2 normalize cho cosine metric
        if self.metric == "cosine":
            norms   = np.linalg.norm(vectors, axis=1, keepdims=True)
            vectors = vectors / (norms + 1e-9)

        if FAISS_OK:
            self._index.add(vectors)
        else:
            # numpy fallback
            if self._vecs is None:
                self._vecs = vectors
            else:
                self._vecs = np.vstack([self._vecs, vectors])

        self.metadata.extend(meta)

    def search(self, query: np.ndarray, top_k: int = 10) -> List[Tuple[float, dict]]:
        """Top-k ANN search. Returns [(score, metadata)] sorted best first."""
        q = query.astype(np.float32).reshape(1, -1)
        if self.metric == "cosine":
            q = q / (np.linalg.norm(q) + 1e-9)

        if FAISS_OK and self._index is not None:
            D, I = self._index.search(q, top_k)
            return [
                (float(D[0][j]), self.metadata[I[0][j]])
                for j in range(len(I[0]))
                if I[0][j] != -1
            ]
        else:
            sims = (self._vecs @ q.T).flatten()
            idx  = np.argsort(sims)[::-1][:top_k]
            return [(float(sims[i]), self.metadata[i]) for i in idx]

    # ── Quantization ───────────────────────────────────────────

    def quantize_to_int8(self) -> "QuantizedIndex":
        """
        Quantize HNSW index xuống INT8.
        Giảm memory ~75%, tăng throughput ~4x.
        Tương tự TensorRT INT8 trong báo cáo.
        """
        if not FAISS_OK or self._index is None:
            print("[WARN] FAISS not available — cannot quantize.")
            return self

        # Wrap với FAISS scalar quantizer (SQ8)
        sq = faiss.IndexScalarQuantizer(
            self.dim,
            faiss.ScalarQuantizer.QT_8bit,
            faiss.METRIC_INNER_PRODUCT,
        )
        # Tạo flat index để train quantizer
        vecs = np.zeros((max(1, len(self.metadata)), self.dim), dtype=np.float32)
        if len(self.metadata) > 0:
            # Reconstruct từ HNSW (nếu có)
            try:
                for i in range(len(self.metadata)):
                    v = self._index.reconstruct(i)
                    vecs[i] = v
                sq.train(vecs)
                sq.add(vecs)
            except Exception:
                print("[WARN] Quantization reconstruction failed — returning original.")
                return self

        q_idx = QuantizedIndex(sq, self.metadata, self.dim)
        print(f"Quantized to INT8: {len(self.metadata)} vectors, dim={self.dim}")
        return q_idx

    # ── Persistence ─────────────────────────────────────────────

    def save(self, index_path: str, meta_path: str):
        os.makedirs(os.path.dirname(index_path) or ".", exist_ok=True)
        if FAISS_OK and self._index is not None:
            faiss.write_index(self._index, index_path)
        elif self._vecs is not None:
            np.save(index_path + ".npy", self._vecs)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        print(f"Saved index → {index_path} | meta → {meta_path}")

    @classmethod
    def load(cls, index_path: str, meta_path: str, dim: int,
             metric: str = "cosine") -> "HNSWIndex":
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        obj = cls.__new__(cls)
        obj.dim      = dim
        obj.metric   = metric
        obj.metadata = meta
        if FAISS_OK and os.path.exists(index_path):
            obj._index = faiss.read_index(index_path)
            obj._vecs  = None
        elif os.path.exists(index_path + ".npy"):
            obj._vecs  = np.load(index_path + ".npy")
            obj._index = None
        else:
            obj._vecs  = None
            obj._index = None
        print(f"Loaded index: {len(meta)} vectors, dim={dim}")
        return obj

    def __len__(self):
        return len(self.metadata)


class QuantizedIndex:
    """Wrapper quanh FAISS ScalarQuantizer index (INT8)."""

    def __init__(self, faiss_index, metadata, dim):
        self._index  = faiss_index
        self.metadata = metadata
        self.dim     = dim

    def search(self, query: np.ndarray, top_k: int = 10):
        q = query.astype(np.float32).reshape(1, -1)
        D, I = self._index.search(q, top_k)
        return [(float(D[0][j]), self.metadata[I[0][j]])
                for j in range(len(I[0])) if I[0][j] != -1]

    def __len__(self):
        return len(self.metadata)


# ═══════════════════════════════════════════════
# 3. Hybrid Vector Store
#    Kết hợp Text + DL embeddings
# ═══════════════════════════════════════════════

class HybridVectorStore:
    """
    Dual index: Text HNSW + DL HNSW → Hybrid scoring.

    score = α × text_score + (1−α) × dl_score

    Lợi ích:
    - Text index: semantic matching (mô tả, tags)
    - DL index  : behavioral matching (user preference patterns)
    - Hybrid    : tốt hơn cả hai đơn lẻ
    """

    def __init__(self, text_dim: int = TEXT_DIM, dl_dim: int = DL_DIM,
                 alpha: float = 0.6):
        """
        alpha : weight của text score (1-alpha là DL score)
        """
        self.text_index = HNSWIndex(text_dim, metric="cosine")
        self.dl_index   = HNSWIndex(dl_dim,   metric="cosine")
        self.alpha      = alpha
        self.metadata   = []

    def add(self, text_vecs: np.ndarray, dl_vecs: Optional[np.ndarray],
            meta: List[dict]):
        """
        Thêm vectors vào cả hai index (incremental — không rebuild).
        dl_vecs có thể None (chỉ dùng text index khi chưa có DL model).
        """
        self.text_index.add(text_vecs, meta)
        if dl_vecs is not None:
            self.dl_index.add(dl_vecs, meta)
        self.metadata = meta   # sync meta list

    def search(self, query_vecs: dict, top_k: int = 10) -> List[Tuple[float, dict]]:
        """
        query_vecs: {"text": (1, D_t), "dl": (1, D_dl) or None}
        Returns: [(hybrid_score, metadata)] sorted best first
        """
        text_results = self.text_index.search(query_vecs["text"], top_k * 2)

        if query_vecs.get("dl") is not None and len(self.dl_index) > 0:
            dl_results   = self.dl_index.search(query_vecs["dl"], top_k * 2)
            dl_scores    = {r[1]["service_id"]: r[0] for r in dl_results}
        else:
            dl_scores = {}

        combined = {}
        for score, meta in text_results:
            sid = meta["service_id"]
            dl  = dl_scores.get(sid, 0.0)
            combined[sid] = (
                self.alpha * score + (1 - self.alpha) * dl,
                meta,
            )

        results = sorted(combined.values(), key=lambda x: x[0], reverse=True)
        return results[:top_k]

    def save(self, text_path: str = TEXT_INDEX, dl_path: str = DL_INDEX,
             meta_path: str = META_PATH):
        self.text_index.save(text_path, meta_path)
        if len(self.dl_index) > 0:
            self.dl_index.save(dl_path, meta_path + ".dl")

    @classmethod
    def load(cls, text_path: str = TEXT_INDEX, dl_path: str = DL_INDEX,
             meta_path: str = META_PATH) -> "HybridVectorStore":
        store = cls()
        store.text_index = HNSWIndex.load(text_path, meta_path, TEXT_DIM)
        store.metadata   = store.text_index.metadata
        if os.path.exists(dl_path):
            store.dl_index = HNSWIndex.load(dl_path, meta_path + ".dl", DL_DIM)
        return store


# ═══════════════════════════════════════════════
# 4. Build Pipeline
# ═══════════════════════════════════════════════

def build_vector_store(
    kb_path: str = KB_JSON,
    text_index_path: str = TEXT_INDEX,
    dl_index_path: str = DL_INDEX,
    meta_path: str = META_PATH,
    model_name: str = EMBED_MODEL,
    dl_vecs: Optional[np.ndarray] = None,   # pre-computed DL embeddings
    use_int8: bool = False,
) -> HybridVectorStore:
    """
    End-to-end build pipeline:
      1. Load KB JSON
      2. Encode với Sentence-Transformers
      3. Optionally add DL embeddings
      4. Build HNSW indexes
      5. Optionally quantize to INT8
      6. Save to disk
    """
    with open(kb_path, encoding="utf-8") as f:
        kb = json.load(f)

    documents = [svc["document"] for svc in kb]
    print(f"Building vector store for {len(kb)} services …")

    encoder   = MultiModalEncoder(model_name)
    text_vecs = encoder.encode_text(documents)
    print(f"Text embeddings: {text_vecs.shape}, dtype={text_vecs.dtype}")

    store = HybridVectorStore(text_dim=text_vecs.shape[1])
    store.add(text_vecs, dl_vecs, kb)

    if use_int8 and FAISS_OK:
        print("Quantizing text index to INT8 …")
        store.text_index = store.text_index.quantize_to_int8()

    store.save(text_index_path, dl_index_path, meta_path)
    print(f"✓ Vector store built: {len(store.text_index)} vectors indexed.\n")
    return store


# ═══════════════════════════════════════════════
# 5. Quick test
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    if not os.path.exists(META_PATH):
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from build_kb import build_knowledge_base
        build_knowledge_base()

    store = build_vector_store()

    encoder = MultiModalEncoder()
    query   = "I want to protect my family's health"
    q_vecs  = encoder.encode_query(query)

    print(f"\nQuery: {query}")
    print("── Top-3 Results ──")
    for score, svc in store.search(q_vecs, top_k=3):
        print(f"  [{score:.4f}] {svc['service_name']} ({svc['category']})")