"""
hybrid_retriever.py — Hybrid retrieval: sparse (TF-IDF) + dense (embeddings) + RRF top-k.
"""
from __future__ import annotations

import os
import pickle
import re
import time
from collections import defaultdict
from typing import Optional

import numpy as np
import requests
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from rag.product_reranker import get_product_reranker

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(BASE, "rag", "catalog_hybrid_index.pkl")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8000")
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
DEFAULT_TOP_K = int(os.getenv("CHAT_TOP_K", "5"))
RRF_K = int(os.getenv("HYBRID_RRF_K", "60"))
RERANK_CANDIDATES = int(os.getenv("RERANK_CANDIDATES", "20"))


def _tokenize_vi(text: str) -> str:
    text = str(text or "").lower()
    text = re.sub(r"[^\wàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _product_doc(raw: dict) -> str:
    category = raw.get("category") or {}
    brand = raw.get("brand") or {}
    cat_name = category.get("name", "") if isinstance(category, dict) else str(category)
    brand_name = brand.get("name", "") if isinstance(brand, dict) else str(brand)
    parts = [
        raw.get("name", ""),
        raw.get("description", ""),
        raw.get("sku", ""),
        cat_name,
        brand_name,
        str(raw.get("attributes", "")),
    ]
    return _tokenize_vi(" ".join(str(p) for p in parts if p))


def _normalize_product(raw: dict, score: float = 0.0) -> dict:
    category = raw.get("category") or {}
    brand = raw.get("brand") or {}
    return {
        "product_id": int(raw["id"]),
        "name": raw.get("name", ""),
        "sku": raw.get("sku", ""),
        "price": raw.get("price", 0),
        "effective_price": raw.get("effective_price", raw.get("price", 0)),
        "description": (raw.get("description") or "")[:280],
        "stock": raw.get("stock", 0),
        "category_id": raw.get("category_id") or (category.get("id") if isinstance(category, dict) else None),
        "category_name": category.get("name", "") if isinstance(category, dict) else "",
        "brand_name": brand.get("name", "") if isinstance(brand, dict) else "",
        "retrieval_score": round(float(score), 4),
    }


class HybridProductRetriever:
    def __init__(self):
        self.catalog: list[dict] = []
        self.docs: list[str] = []
        self.product_ids: list[int] = []
        self._tfidf: Optional[TfidfVectorizer] = None
        self._tfidf_matrix = None
        self._embeddings: Optional[np.ndarray] = None
        self._svd: Optional[TruncatedSVD] = None
        self._embedding_mode = "none"  # transformer | svd | none
        self._encoder = None
        self._built_at = 0.0
        self._loaded = False

    def ensure_index(self, force: bool = False) -> bool:
        if self._loaded and not force:
            return bool(self.catalog)
        if not force and os.path.isfile(INDEX_PATH):
            try:
                with open(INDEX_PATH, "rb") as f:
                    data = pickle.load(f)
                self.catalog = data.get("catalog", [])
                self.docs = data.get("docs", [])
                self.product_ids = data.get("product_ids", [])
                self._tfidf = data.get("tfidf")
                self._tfidf_matrix = data.get("tfidf_matrix")
                self._embeddings = data.get("embeddings")
                self._svd = data.get("svd")
                self._embedding_mode = data.get("embedding_mode", "none")
                self._built_at = data.get("built_at", 0)
                self._loaded = True
                if self.catalog:
                    print(f"[hybrid] Loaded index: {len(self.catalog)} products")
                    return True
            except Exception as exc:
                print(f"[hybrid] Failed to load index: {exc}")
        return self.rebuild_index(force=True)

    def _fetch_all_products(self) -> list[dict]:
        items = []
        page = 1
        while page <= 10:
            try:
                r = requests.get(
                    f"{PRODUCT_SERVICE_URL.rstrip('/')}/products/",
                    params={"page_size": 200, "page": page},
                    timeout=10,
                )
                if r.status_code != 200:
                    break
                data = r.json()
                batch = data.get("results", data) if isinstance(data, dict) else data
                if not isinstance(batch, list) or not batch:
                    break
                items.extend(batch)
                total_pages = int(data.get("total_pages", 1)) if isinstance(data, dict) else 1
                if page >= total_pages:
                    break
                page += 1
            except requests.exceptions.RequestException as exc:
                print(f"[hybrid] fetch products failed: {exc}")
                break
        return [p for p in items if isinstance(p, dict) and p.get("id") is not None]

    def rebuild_index(self, force: bool = False) -> bool:
        print("[hybrid] Rebuilding catalog index from product-service...")
        raw_products = self._fetch_all_products()
        if not raw_products:
            print("[hybrid] No products fetched — index not built")
            return False

        self.catalog = raw_products
        self.product_ids = [int(p["id"]) for p in raw_products]
        self.docs = [_product_doc(p) for p in raw_products]

        self._tfidf = TfidfVectorizer(
            analyzer="word",
            token_pattern=r"(?u)\b\w+\b",
            ngram_range=(1, 2),
            max_features=8000,
            sublinear_tf=True,
        )
        self._tfidf_matrix = self._tfidf.fit_transform(self.docs)

        try:
            from sentence_transformers import SentenceTransformer

            if self._encoder is None:
                print(f"[hybrid] Loading embedding model: {EMBEDDING_MODEL}")
                self._encoder = SentenceTransformer(EMBEDDING_MODEL)
            texts = [f"passage: {d}" for d in self.docs]
            self._embeddings = self._encoder.encode(
                texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True
            )
            self._embedding_mode = "transformer"
            self._svd = None
        except Exception as exc:
            print(f"[hybrid] Transformer embeddings failed ({exc}) — using SVD fallback")
            self._build_svd_embeddings()

        self._built_at = time.time()
        self._loaded = True
        self._save_index()
        print(f"[hybrid] Index built: {len(self.catalog)} products")
        return True

    def _build_svd_embeddings(self):
        n_features = self._tfidf_matrix.shape[1] if self._tfidf_matrix is not None else 0
        if n_features < 2:
            self._embeddings = None
            self._svd = None
            self._embedding_mode = "none"
            return
        n_components = min(96, n_features - 1, max(2, len(self.docs) - 1))
        self._svd = TruncatedSVD(n_components=n_components, random_state=42)
        self._embeddings = self._svd.fit_transform(self._tfidf_matrix)
        norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._embeddings = self._embeddings / norms
        self._embedding_mode = "svd"
        print(f"[hybrid] SVD embeddings: {n_components} dims")

    def _save_index(self):
        try:
            os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
            with open(INDEX_PATH, "wb") as f:
                pickle.dump(
                    {
                        "catalog": self.catalog,
                        "docs": self.docs,
                        "product_ids": self.product_ids,
                        "tfidf": self._tfidf,
                        "tfidf_matrix": self._tfidf_matrix,
                        "embeddings": self._embeddings,
                        "svd": self._svd,
                        "embedding_mode": self._embedding_mode,
                        "built_at": self._built_at,
                        "model_name": EMBEDDING_MODEL,
                    },
                    f,
                )
        except Exception as exc:
            print(f"[hybrid] Failed to save index: {exc}")

    def _sparse_search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        if self._tfidf is None or self._tfidf_matrix is None:
            return []
        q = _tokenize_vi(query)
        if not q:
            return []
        q_vec = self._tfidf.transform([q])
        scores = cosine_similarity(q_vec, self._tfidf_matrix).flatten()
        ranked = sorted(enumerate(scores), key=lambda x: -x[1])
        return [(self.product_ids[i], float(s)) for i, s in ranked[: top_k * 3] if s > 0]

    def _dense_search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        if self._embeddings is None:
            return []
        try:
            q = _tokenize_vi(query)
            if not q:
                return []

            if self._embedding_mode == "transformer":
                if self._encoder is None:
                    from sentence_transformers import SentenceTransformer
                    self._encoder = SentenceTransformer(EMBEDDING_MODEL)
                q_emb = self._encoder.encode(
                    [f"query: {q}"],
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )[0]
                scores = np.dot(self._embeddings, q_emb)
            elif self._embedding_mode == "svd" and self._svd is not None and self._tfidf is not None:
                q_vec = self._tfidf.transform([q])
                q_emb = self._svd.transform(q_vec)[0]
                norm = np.linalg.norm(q_emb)
                if norm > 0:
                    q_emb = q_emb / norm
                scores = np.dot(self._embeddings, q_emb)
            else:
                return []

            ranked = sorted(enumerate(scores), key=lambda x: -x[1])
            return [(self.product_ids[i], float(s)) for i, s in ranked[: top_k * 3] if s > 0.02]
        except Exception as exc:
            print(f"[hybrid] dense search failed: {exc}")
            return []

    @staticmethod
    def _rrf_fusion(rank_lists: list[list[int]], top_k: int, rrf_k: int = RRF_K) -> list[tuple[int, float]]:
        scores: dict[int, float] = defaultdict(float)
        for ranks in rank_lists:
            for rank, pid in enumerate(ranks):
                scores[pid] += 1.0 / (rrf_k + rank + 1)
        ordered = sorted(scores.items(), key=lambda x: -x[1])
        return ordered[:top_k]

    def hybrid_search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        min_score: float = 0.0,
    ) -> tuple[list[dict], float]:
        if not self.ensure_index():
            return [], 0.0

        query = str(query or "").strip()
        if not query:
            return [], 0.0

        candidate_k = max(top_k * 4, RERANK_CANDIDATES)
        sparse = self._sparse_search(query, candidate_k)
        dense = self._dense_search(query, candidate_k)

        sparse_map = {pid: score for pid, score in sparse}
        dense_map = {pid: score for pid, score in dense}
        sparse_ranks = [pid for pid, _ in sparse]
        dense_ranks = [pid for pid, _ in dense]
        rank_lists = [r for r in (sparse_ranks, dense_ranks) if r]
        if not rank_lists:
            return [], 0.0

        fused = self._rrf_fusion(rank_lists, top_k=candidate_k)
        id_to_raw = {int(p["id"]): p for p in self.catalog}

        candidates = []
        rrf_map = {}
        for pid, score in fused:
            if score < min_score:
                continue
            raw = id_to_raw.get(pid)
            if raw:
                candidates.append(_normalize_product(raw, score))
                rrf_map[pid] = score

        if not candidates:
            return [], 0.0

        reranked = get_product_reranker().rerank(
            query=query,
            products=candidates,
            top_k=top_k,
            sparse_scores=sparse_map,
            dense_scores=dense_map,
            rrf_scores=rrf_map,
        )
        if len(reranked) > 1:
            top_score = float(reranked[0].get("rerank_score", reranked[0].get("retrieval_score", 0)) or 0)
            cutoff = max(top_score * 0.4, 1.0)
            filtered = [
                p for p in reranked
                if float(p.get("rerank_score", p.get("retrieval_score", 0)) or 0) >= cutoff
            ]
            if filtered:
                reranked = filtered
        max_score = reranked[0].get("rerank_score", reranked[0].get("retrieval_score", 0)) if reranked else 0.0
        return reranked, float(max_score)

    def fetch_products_by_ids(self, product_ids: list, limit: int = 5) -> list[dict]:
        if not self.ensure_index():
            return []
        id_to_raw = {int(p["id"]): p for p in self.catalog}
        out = []
        for pid in product_ids:
            try:
                pid_int = int(pid)
            except (TypeError, ValueError):
                continue
            raw = id_to_raw.get(pid_int)
            if raw:
                out.append(_normalize_product(raw))
            if len(out) >= limit:
                break
        return out


_retriever: Optional[HybridProductRetriever] = None


def get_hybrid_retriever() -> HybridProductRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridProductRetriever()
    return _retriever
