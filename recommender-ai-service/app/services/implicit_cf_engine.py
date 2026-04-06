"""
Matrix factorization (NMF trên ma trận user–item) — train offline từ CSV,
load tại runtime để trộn với co-purchase + behavior.

Artifacts trong IMPLICIT_CF_DATA_DIR:
  - factors.npz        : W (users×K), H (K×items)
  - interactions.npz   : ma trận CSR đã train
  - meta.json          : mapping id, optional dataset_book_id → local book_id
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
from scipy.sparse import load_npz

logger = logging.getLogger(__name__)

FACTORS_NAME = "factors.npz"
INTERACTIONS_NAME = "interactions.npz"
META_NAME = "meta.json"


class ImplicitCFEngine:
    def __init__(self, data_dir: Path | str):
        self.data_dir = Path(data_dir)
        self._W: np.ndarray | None = None
        self._H: np.ndarray | None = None
        self._interactions = None
        self._meta: dict | None = None
        self._mtime = 0.0

    def is_ready(self) -> bool:
        return (
            (self.data_dir / FACTORS_NAME).is_file()
            and (self.data_dir / INTERACTIONS_NAME).is_file()
            and (self.data_dir / META_NAME).is_file()
        )

    def reload(self) -> None:
        if not self.is_ready():
            self._W = self._H = None
            self._interactions = None
            self._meta = None
            return

        paths = [
            self.data_dir / FACTORS_NAME,
            self.data_dir / INTERACTIONS_NAME,
            self.data_dir / META_NAME,
        ]
        mtime = max(p.stat().st_mtime for p in paths)
        if self._W is not None and mtime <= self._mtime:
            return

        with open(self.data_dir / META_NAME, encoding="utf-8") as f:
            self._meta = json.load(f)
        fac = np.load(self.data_dir / FACTORS_NAME)
        self._W = np.asarray(fac["W"])
        self._H = np.asarray(fac["H"])
        self._interactions = load_npz(self.data_dir / INTERACTIONS_NAME)
        self._mtime = mtime
        logger.info("Matrix CF (NMF) loaded from %s", self.data_dir)

    def _local_id_for_col(self, col_idx: int) -> int:
        assert self._meta is not None
        idx_to_book: list = self._meta["idx_to_book_id"]
        ds_bid = int(idx_to_book[col_idx])
        book_map: dict = self._meta.get("dataset_book_id_to_local_book_id") or {}
        raw = book_map.get(str(ds_bid), book_map.get(ds_bid))
        return int(raw) if raw is not None else ds_bid

    def recommend(
        self,
        customer_id: int,
        exclude_book_ids: set,
        limit: int,
    ) -> list[tuple[int, float]]:
        self.reload()
        if self._W is None or self._H is None or self._meta is None or self._interactions is None:
            return []

        u2i = self._meta.get("user_id_to_idx") or {}
        key = str(customer_id)
        if key not in u2i:
            return []
        uidx = int(u2i[key])

        n_users, n_items = self._interactions.shape
        if uidx >= n_users:
            return []

        scores = (self._W[uidx] @ self._H).ravel()
        liked = set(self._interactions[uidx].nonzero()[1].tolist())

        for j in range(n_items):
            if j in liked:
                scores[j] = -np.inf
                continue
            if self._local_id_for_col(j) in exclude_book_ids:
                scores[j] = -np.inf

        order = np.argsort(-scores)
        out: list[tuple[int, float]] = []
        for j in order:
            if not np.isfinite(scores[j]):
                continue
            local_bid = self._local_id_for_col(int(j))
            if local_bid in exclude_book_ids:
                continue
            out.append((local_bid, float(scores[j])))
            if len(out) >= limit:
                break
        return out


_engine: ImplicitCFEngine | None = None


def get_implicit_engine() -> ImplicitCFEngine:
    global _engine
    if _engine is None:
        from django.conf import settings

        _engine = ImplicitCFEngine(settings.IMPLICIT_CF_DATA_DIR)
    return _engine
