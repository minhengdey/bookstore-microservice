import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import torch
import torch.nn as nn
import torch.nn.functional as F

from data_sync import build_graph_training_payload


@dataclass
class GNNConfig:
    hidden_dim: int = 64
    epochs: int = 40
    lr: float = 1e-2
    weight_decay: float = 1e-4


class BipartiteGNN(nn.Module):
    def __init__(self, n_users: int, n_books: int, hidden_dim: int):
        super().__init__()
        self.user_emb = nn.Embedding(max(1, n_users), hidden_dim)
        self.book_emb = nn.Embedding(max(1, n_books), hidden_dim)
        self.user_proj = nn.Linear(hidden_dim, hidden_dim)
        self.book_proj = nn.Linear(hidden_dim, hidden_dim)

    def forward(self):
        u = self.user_proj(self.user_emb.weight)
        b = self.book_proj(self.book_emb.weight)
        return F.normalize(u, dim=-1), F.normalize(b, dim=-1)


class GNNTrainer:
    def __init__(self, artifact_dir: str):
        self.artifact_dir = Path(artifact_dir)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.model_path = self.artifact_dir / "gnn_recommender.pt"
        self.meta_path = self.artifact_dir / "gnn_meta.json"

    def train(self, cfg: GNNConfig | None = None) -> Dict:
        cfg = cfg or GNNConfig()
        payload = build_graph_training_payload()
        users = payload["users"]
        books = payload["books"]
        edges = payload["user_book_edges"]

        user_to_idx = {uid: i for i, uid in enumerate(users)}
        book_to_idx = {b["book_id"]: i for i, b in enumerate(books)}
        if not users or not books or not edges:
            empty_meta = {"user_to_idx": user_to_idx, "book_to_idx": book_to_idx, "training_loss": None}
            self.meta_path.write_text(json.dumps(empty_meta, ensure_ascii=False, indent=2), encoding="utf-8")
            return empty_meta

        model = BipartiteGNN(n_users=len(users), n_books=len(books), hidden_dim=cfg.hidden_dim)
        optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)

        positives = []
        for e in edges:
            if e["user_id"] in user_to_idx and e["book_id"] in book_to_idx:
                positives.append((user_to_idx[e["user_id"]], book_to_idx[e["book_id"]], float(e["weight"])))
        if not positives:
            return {"user_to_idx": user_to_idx, "book_to_idx": book_to_idx, "training_loss": None}

        for _ in range(cfg.epochs):
            model.train()
            u_emb, b_emb = model()
            loss = torch.tensor(0.0)
            for u_idx, b_idx, w in positives:
                pos_score = (u_emb[u_idx] * b_emb[b_idx]).sum()
                neg_b_idx = torch.randint(0, len(books), (1,)).item()
                neg_score = (u_emb[u_idx] * b_emb[neg_b_idx]).sum()
                sample_loss = -torch.log(torch.sigmoid(pos_score - neg_score) + 1e-9) * w
                loss = loss + sample_loss
            loss = loss / max(len(positives), 1)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        torch.save(model.state_dict(), self.model_path)
        meta = {
            "user_to_idx": user_to_idx,
            "book_to_idx": book_to_idx,
            "hidden_dim": cfg.hidden_dim,
            "training_loss": float(loss.detach()),
        }
        self.meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return meta

    def predict_for_user(self, user_id: int, top_k: int = 20) -> Dict[int, float]:
        if not self.model_path.exists() or not self.meta_path.exists():
            return {}
        meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
        user_to_idx = {int(k): v for k, v in meta.get("user_to_idx", {}).items()}
        book_to_idx = {int(k): v for k, v in meta.get("book_to_idx", {}).items()}
        if user_id not in user_to_idx or not book_to_idx:
            return {}

        model = BipartiteGNN(
            n_users=max(len(user_to_idx), 1),
            n_books=max(len(book_to_idx), 1),
            hidden_dim=int(meta.get("hidden_dim", 64)),
        )
        state = torch.load(self.model_path, map_location="cpu")
        model.load_state_dict(state)
        model.eval()
        with torch.no_grad():
            u_emb, b_emb = model()
            u_vec = u_emb[user_to_idx[user_id]]
            scores = torch.matmul(b_emb, u_vec)
            top_vals, top_idx = torch.topk(scores, k=min(top_k, scores.size(0)))
        idx_to_book = {idx: bid for bid, idx in book_to_idx.items()}
        return {
            int(idx_to_book[int(i)]): float(v)
            for i, v in zip(top_idx.tolist(), top_vals.tolist())
            if int(i) in idx_to_book
        }
