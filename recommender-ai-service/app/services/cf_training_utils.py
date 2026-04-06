"""Chung cho train_implicit_cf và train_implicit_cf_local (NMF + lưu artifact)."""
import json
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix, save_npz
from sklearn.decomposition import NMF


def save_nmf_model(
    matrix: csr_matrix,
    user_id_to_idx: dict[str, int],
    idx_to_book_id: list[int],
    out_dir: Path,
    extra_meta: dict,
    factors: int = 64,
    max_iter: int = 200,
) -> int:
    """
    Train NMF, ghi factors.npz, interactions.npz, meta.json.
    Trả về n_components đã dùng.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    n_users, n_items = matrix.shape
    n_comp = min(int(factors), n_users, n_items) - 1
    if n_comp < 2:
        n_comp = min(2, n_users, n_items)
    n_comp = max(2, n_comp)

    nmf = NMF(
        n_components=n_comp,
        init="random",
        random_state=42,
        max_iter=max_iter,
        alpha_W=0.01,
        alpha_H=0.01,
    )
    W = nmf.fit_transform(matrix)
    H = nmf.components_

    meta = {
        "backend": "nmf",
        "user_id_to_idx": user_id_to_idx,
        "idx_to_book_id": idx_to_book_id,
        "n_users": n_users,
        "n_items": n_items,
        "n_components": int(n_comp),
        "dataset_book_id_to_local_book_id": {},
        **extra_meta,
    }

    np.savez_compressed(out_dir / "factors.npz", W=W, H=H)
    save_npz(out_dir / "interactions.npz", matrix)
    with open(out_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return n_comp
