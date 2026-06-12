"""
product_reranker.py — Rerank top candidates sau hybrid retrieval.

Ưu tiên Cross-Encoder (sentence-transformers); fallback feature-based khi GPU/torch lỗi.
"""
from __future__ import annotations

import os
import re
from typing import Optional

RERANKER_MODEL = os.getenv(
    "RERANKER_MODEL",
    "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
)
RERANK_ENABLED = os.getenv("RERANK_ENABLED", "true").lower() in ("1", "true", "yes")


def _tokenize(text: str) -> list[str]:
    raw = str(text or "").lower()
    raw = re.sub(
        r"[^\wàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]+",
        " ",
        raw,
    )
    return [t for t in raw.split() if len(t) >= 2]


def _product_passage(product: dict) -> str:
    parts = [
        product.get("name", ""),
        product.get("description", ""),
        product.get("category_name", ""),
        product.get("brand_name", ""),
        product.get("sku", ""),
    ]
    return ". ".join(str(p).strip() for p in parts if p)


def _normalize_scores(score_map: dict[int, float]) -> dict[int, float]:
    if not score_map:
        return {}
    vals = list(score_map.values())
    lo, hi = min(vals), max(vals)
    if hi <= lo:
        return {k: 1.0 for k in score_map}
    return {k: (v - lo) / (hi - lo) for k, v in score_map.items()}


class ProductReranker:
    def __init__(self):
        self._cross_encoder = None
        self._mode = "feature"  # cross_encoder | feature
        self._load_attempted = False

    def _try_load_cross_encoder(self) -> bool:
        if self._load_attempted:
            return self._mode == "cross_encoder"
        self._load_attempted = True
        try:
            from sentence_transformers import CrossEncoder

            print(f"[reranker] Loading Cross-Encoder: {RERANKER_MODEL}")
            self._cross_encoder = CrossEncoder(RERANKER_MODEL)
            self._mode = "cross_encoder"
            print("[reranker] Cross-Encoder ready")
            return True
        except Exception as exc:
            print(f"[reranker] Cross-Encoder unavailable ({exc}) — using feature reranker")
            self._mode = "feature"
            return False

    def _feature_scores(
        self,
        query: str,
        products: list[dict],
        sparse_scores: dict[int, float],
        dense_scores: dict[int, float],
        rrf_scores: dict[int, float],
    ) -> list[float]:
        q_tokens = _tokenize(query)
        q_phrase = " ".join(q_tokens)
        sparse_n = _normalize_scores(sparse_scores)
        dense_n = _normalize_scores(dense_scores)
        rrf_n = _normalize_scores(rrf_scores)

        scores = []
        for p in products:
            pid = int(p["product_id"])
            name = str(p.get("name") or "").lower()
            desc = str(p.get("description") or "").lower()
            cat = str(p.get("category_name") or "").lower()
            blob = f"{name} {desc} {cat}"

            overlap = sum(1 for t in q_tokens if t in blob)
            phrase_bonus = 3.0 if q_phrase and q_phrase in blob else 0.0
            name_bonus = sum(2.0 for t in q_tokens if t in name)
            stock_bonus = 0.15 if int(p.get("stock") or 0) > 0 else 0.0

            score = (
                rrf_n.get(pid, 0.0) * 3.5
                + sparse_n.get(pid, 0.0) * 2.5
                + dense_n.get(pid, 0.0) * 2.0
                + overlap * 0.35
                + phrase_bonus
                + name_bonus
                + stock_bonus
            )
            scores.append(score)
        return scores

    def rerank(
        self,
        query: str,
        products: list[dict],
        top_k: int = 5,
        sparse_scores: dict[int, float] | None = None,
        dense_scores: dict[int, float] | None = None,
        rrf_scores: dict[int, float] | None = None,
    ) -> list[dict]:
        if not RERANK_ENABLED or not products:
            return products[:top_k]

        query = str(query or "").strip()
        if not query:
            return products[:top_k]

        sparse_scores = sparse_scores or {}
        dense_scores = dense_scores or {}
        rrf_scores = rrf_scores or {}

        final_scores: list[float] = []
        if self._try_load_cross_encoder() and self._cross_encoder is not None:
            try:
                pairs = [[query, _product_passage(p)] for p in products]
                ce_scores = self._cross_encoder.predict(pairs)
                final_scores = [float(s) for s in ce_scores]
            except Exception as exc:
                print(f"[reranker] Cross-Encoder predict failed ({exc}) — feature fallback")
                final_scores = self._feature_scores(
                    query, products, sparse_scores, dense_scores, rrf_scores
                )
        else:
            final_scores = self._feature_scores(
                query, products, sparse_scores, dense_scores, rrf_scores
            )

        ranked = sorted(
            zip(products, final_scores),
            key=lambda row: -row[1],
        )
        out = []
        for product, score in ranked[:top_k]:
            item = dict(product)
            item["retrieval_score"] = round(float(score), 4)
            item["rerank_score"] = round(float(score), 4)
            out.append(item)
        return out


_reranker: Optional[ProductReranker] = None


def get_product_reranker() -> ProductReranker:
    global _reranker
    if _reranker is None:
        _reranker = ProductReranker()
    return _reranker
