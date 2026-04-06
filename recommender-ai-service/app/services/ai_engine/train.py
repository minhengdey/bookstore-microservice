"""
train.py  (v2 — Multi-stage Training)
--------------------------------------
Pipeline training 3 stage theo báo cáo:

  Stage 1 (Recall)     : Two-Tower với InfoNCE loss
  Stage 2 (Ranking)    : DIN với Multi-task loss (CTR + CVR + Category + Rec)
  Stage 3 (Re-ranking) : Dueling DQN với Experience Replay

Metrics:
  - Recall   : AUC, Recall@K
  - Ranking  : AUC-CTR, AUC-CVR, Accuracy (category)
  - DQN      : Mean Q-value, Episode reward
  - Shared   : NDCG@K, Hit-Rate@K
"""

import os
import sys
import math
import random
import collections
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingWarmRestarts

# Đảm bảo import hoạt động khi gọi từ bất kỳ đâu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from model_behavior import (
    ModelConfig, CustomerBehaviorPipeline,
    RecallLoss, RankingLoss, DQNLoss,
)

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)


# ═══════════════════════════════════════════════════════════════
# 1. Dataset — Synthetic Customer Behavior
# ═══════════════════════════════════════════════════════════════

class CustomerBehaviorDataset(Dataset):
    """
    Dataset tổng hợp với đầy đủ labels cho cả 3 stage.
    Trong production: thay bằng Kafka consumer / Feature Store.
    """

    def __init__(self, cfg: ModelConfig, n: int = 4000, max_seq: int = 20,
                 service_feat_dim: int = 32, context_dim: int = 8):
        self.cfg = cfg
        self.n   = n
        self.max_seq      = max_seq
        self.svc_feat_dim = service_feat_dim
        self.ctx_dim      = context_dim
        self._generate()

    def _generate(self):
        cfg, n, T = self.cfg, self.n, self.max_seq

        # User scalars
        self.user_ids     = torch.randint(1, cfg.num_users,     (n,))
        self.ages         = torch.rand(n, 1)
        self.genders      = torch.randint(0, 2, (n, 1)).float()
        self.loc_ids      = torch.randint(1, cfg.num_locations, (n,))

        # Sequential histories
        p_seqs, p_lens, b_seqs, b_lens = [], [], [], []
        for _ in range(n):
            pl = random.randint(3, T)
            bl = random.randint(3, T)
            p  = torch.zeros(T, dtype=torch.long)
            b  = torch.zeros(T, dtype=torch.long)
            p[:pl] = torch.randint(1, cfg.num_items, (pl,))
            b[:bl] = torch.randint(1, cfg.num_items, (bl,))
            p_seqs.append(p); p_lens.append(pl)
            b_seqs.append(b); b_lens.append(bl)

        self.purchase_ids  = torch.stack(p_seqs)
        self.purchase_lens = torch.tensor(p_lens)
        self.browsing_ids  = torch.stack(b_seqs)
        self.browsing_lens = torch.tensor(b_lens)

        # Service features (price, popularity, etc.)
        self.target_svc_ids  = torch.randint(1, cfg.num_services, (n,))
        self.target_cat_ids  = (self.target_svc_ids % cfg.num_service_categories).long()
        self.svc_features    = torch.rand(n, self.svc_feat_dim)
        self.context_feats   = torch.rand(n, self.ctx_dim)

        # Labels
        self.ctr_labels  = torch.randint(0, 2, (n,))            # 0/1
        self.cvr_labels  = self.ctr_labels * torch.randint(0, 2, (n,))  # cvr only if ctr
        self.cat_labels  = self.target_cat_ids
        self.svc_labels  = torch.zeros(n, cfg.num_services)
        for i in range(n):
            k = random.randint(1, 3)
            self.svc_labels[i, random.sample(range(cfg.num_services), k)] = 1.0

        # DQN
        self.dqn_actions  = torch.randint(0, cfg.num_actions, (n,))
        self.dqn_rewards  = torch.rand(n) * 2 - 0.5   # [-0.5, 1.5]

    def __len__(self):
        return self.n

    def __getitem__(self, idx):
        return {
            # User features
            "user_id"         : self.user_ids[idx],
            "age"             : self.ages[idx],
            "gender"          : self.genders[idx],
            "location_id"     : self.loc_ids[idx],
            "purchase_ids"    : self.purchase_ids[idx],
            "purchase_lens"   : self.purchase_lens[idx],
            "browsing_ids"    : self.browsing_ids[idx],
            "browsing_lens"   : self.browsing_lens[idx],
            # Service features
            "target_svc_id"   : self.target_svc_ids[idx],
            "target_cat_id"   : self.target_cat_ids[idx],
            "svc_features"    : self.svc_features[idx],
            "context_feats"   : self.context_feats[idx],
            # Labels
            "ctr_label"       : self.ctr_labels[idx],
            "cvr_label"       : self.cvr_labels[idx],
            "cat_label"       : self.cat_labels[idx],
            "svc_label"       : self.svc_labels[idx],
            # DQN
            "dqn_action"      : self.dqn_actions[idx],
            "dqn_reward"      : self.dqn_rewards[idx],
        }


# ═══════════════════════════════════════════════════════════════
# 2. Metrics
# ═══════════════════════════════════════════════════════════════

def compute_auc(logits: torch.Tensor, labels: torch.Tensor) -> float:
    """Binary AUC via rank-based formula (no sklearn needed)."""
    probs  = torch.sigmoid(logits).cpu().numpy()
    labels = labels.cpu().numpy()
    pos_idx = np.where(labels == 1)[0]
    neg_idx = np.where(labels == 0)[0]
    if len(pos_idx) == 0 or len(neg_idx) == 0:
        return 0.5
    # Sample-efficient: compare all pos vs neg pairs
    pos_scores = probs[pos_idx]
    neg_scores = probs[neg_idx]
    wins  = (pos_scores[:, None] > neg_scores[None, :]).sum()
    ties  = (pos_scores[:, None] == neg_scores[None, :]).sum()
    total = len(pos_idx) * len(neg_idx)
    return float((wins + 0.5 * ties) / total)


def ndcg_at_k(scores: torch.Tensor, targets: torch.Tensor, k: int = 5) -> float:
    B = scores.size(0)
    topk = scores.topk(k, dim=-1).indices
    vals = []
    for i in range(B):
        rel  = targets[i][topk[i]].cpu().numpy()
        dcg  = sum(r / math.log2(j + 2) for j, r in enumerate(rel))
        ideal = sorted(targets[i].cpu().numpy(), reverse=True)[:k]
        idcg = sum(r / math.log2(j + 2) for j, r in enumerate(ideal))
        vals.append(dcg / idcg if idcg > 0 else 0.0)
    return float(np.mean(vals))


def recall_at_k(scores: torch.Tensor, targets: torch.Tensor, k: int = 5) -> float:
    """Fraction of users with ≥1 relevant item in top-k."""
    topk = scores.topk(k, dim=-1).indices
    hits = sum(
        1 for i in range(len(scores))
        if set(topk[i].tolist()) & set(targets[i].nonzero(as_tuple=True)[0].tolist())
    )
    return hits / len(scores)


# ═══════════════════════════════════════════════════════════════
# 3. Experience Replay Buffer (DQN)
# ═══════════════════════════════════════════════════════════════

Transition = collections.namedtuple(
    "Transition", ["state", "action", "reward", "next_state", "done"]
)


class ReplayBuffer:
    """Fixed-size circular buffer cho Experience Replay."""

    def __init__(self, capacity: int = 10_000):
        self.buf = collections.deque(maxlen=capacity)

    def push(self, *args):
        self.buf.append(Transition(*args))

    def sample(self, batch_size: int):
        batch = random.sample(self.buf, batch_size)
        return Transition(*zip(*batch))

    def __len__(self):
        return len(self.buf)


# ═══════════════════════════════════════════════════════════════
# 4. Training Helpers
# ═══════════════════════════════════════════════════════════════

def to_device(batch: dict, device: torch.device) -> dict:
    return {k: v.to(device) for k, v in batch.items()}


def build_user_batch(batch: dict):
    return dict(
        user_ids      = batch["user_id"],
        ages          = batch["age"],
        genders       = batch["gender"],
        location_ids  = batch["location_id"],
        purchase_ids  = batch["purchase_ids"],
        purchase_lens = batch["purchase_lens"],
        browsing_ids  = batch["browsing_ids"],
        browsing_lens = batch["browsing_lens"],
    )


def build_svc_batch(batch: dict):
    return dict(
        service_ids      = batch["target_svc_id"],
        category_ids     = batch["target_cat_id"],
        service_features = batch["svc_features"],
    )


# ═══════════════════════════════════════════════════════════════
# 5. Stage-specific Train / Validate
# ═══════════════════════════════════════════════════════════════

# ── Stage 1: Recall (Two-Tower + InfoNCE) ────────────────────

def train_recall_epoch(model, loader, opt, criterion, device):
    model.train()
    total = 0.0
    for batch in loader:
        batch = to_device(batch, device)
        opt.zero_grad()
        logits, _, _ = model.forward_recall(build_user_batch(batch), build_svc_batch(batch))
        loss = criterion(logits)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        total += loss.item()
    return total / len(loader)


# ── Stage 2: Ranking (DIN) ───────────────────────────────────

def train_ranking_epoch(model, loader, opt, criterion, device):
    model.train()
    total_loss = 0.0
    all_ctr_logits, all_ctr_labels = [], []
    all_svc_scores, all_svc_labels = [], []

    for batch in loader:
        batch = to_device(batch, device)
        opt.zero_grad()

        # Get user embeddings (detach from recall stage to isolate ranking grad)
        with torch.no_grad():
            u_emb = model.get_user_embedding(**build_user_batch(batch))

        ctr, cvr, cat, svc = model.forward_ranking(
            u_emb,
            batch["target_svc_id"],
            batch["purchase_ids"], batch["purchase_lens"],
            batch["browsing_ids"],  batch["browsing_lens"],
            batch["context_feats"],
        )

        loss, _ = criterion(
            ctr, cvr, cat, svc,
            batch["ctr_label"], batch["cvr_label"],
            batch["cat_label"], batch["svc_label"],
        )
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()

        total_loss += loss.item()
        all_ctr_logits.append(ctr.detach().cpu())
        all_ctr_labels.append(batch["ctr_label"].cpu())
        all_svc_scores.append(svc.detach().cpu())
        all_svc_labels.append(batch["svc_label"].cpu())

    auc   = compute_auc(torch.cat(all_ctr_logits), torch.cat(all_ctr_labels))
    ndcg  = ndcg_at_k(torch.cat(all_svc_scores), torch.cat(all_svc_labels), k=5)
    hr    = recall_at_k(torch.cat(all_svc_scores), torch.cat(all_svc_labels), k=5)
    return total_loss / len(loader), auc, ndcg, hr


# ── Stage 3: DQN (Dueling DQN + Replay) ─────────────────────

def train_dqn_step(model, target_model, replay_buffer, opt,
                   criterion, device, batch_size=64, gamma=0.99):
    """One gradient step trên DQN với Double DQN update."""
    if len(replay_buffer) < batch_size:
        return None

    trans  = replay_buffer.sample(batch_size)
    states = torch.stack(trans.state).to(device)
    acts   = torch.tensor(trans.action, dtype=torch.long, device=device)
    rews   = torch.tensor(trans.reward, dtype=torch.float, device=device)
    next_s = torch.stack(trans.next_state).to(device)
    dones  = torch.tensor(trans.done,   dtype=torch.float, device=device)

    # Double DQN: online model chọn action, target model đánh giá
    with torch.no_grad():
        next_actions = model.dqn(next_s).argmax(dim=-1)
        next_q       = target_model.dqn(next_s).gather(1, next_actions.unsqueeze(1)).squeeze(1)
        td_target    = rews + gamma * next_q * (1 - dones)

    q_pred = model.dqn(states)
    loss   = criterion(q_pred, acts, td_target.detach())

    opt.zero_grad()
    loss.backward()
    nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    opt.step()

    return loss.item()


def soft_update_target(model, target_model, tau=0.005):
    """Polyak averaging để update target network."""
    for p, tp in zip(model.parameters(), target_model.parameters()):
        tp.data.copy_(tau * p.data + (1 - tau) * tp.data)


# ═══════════════════════════════════════════════════════════════
# 6. Main Training Entry Point
# ═══════════════════════════════════════════════════════════════

def train(
    recall_epochs    : int   = 10,
    ranking_epochs   : int   = 15,
    dqn_steps        : int   = 5000,
    batch_size       : int   = 64,
    lr               : float = 3e-4,
    weight_decay     : float = 1e-4,
    save_dir         : str   = "checkpoints",
    n_train          : int   = 4000,
    n_val            : int   = 800,
):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    cfg   = ModelConfig()
    model = CustomerBehaviorPipeline(cfg).to(device)

    # Target network cho DQN (frozen copy, updated slowly)
    import copy
    target_model = copy.deepcopy(model).to(device)
    for p in target_model.parameters():
        p.requires_grad_(False)

    # Data
    train_ds = CustomerBehaviorDataset(cfg, n=n_train)
    val_ds   = CustomerBehaviorDataset(cfg, n=n_val)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,  num_workers=0)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False, num_workers=0)

    os.makedirs(save_dir, exist_ok=True)

    # ── STAGE 1: Recall ──────────────────────────────────────
    print("\n" + "═"*55)
    print("  STAGE 1 — Two-Tower Recall Training (InfoNCE)")
    print("═"*55)
    recall_criterion = RecallLoss()
    recall_opt = AdamW(
        list(model.dual_tower.parameters()),
        lr=lr, weight_decay=weight_decay
    )
    recall_sched = CosineAnnealingWarmRestarts(recall_opt, T_0=recall_epochs)

    best_recall_loss = float("inf")
    for epoch in range(1, recall_epochs + 1):
        loss = train_recall_epoch(model, train_loader, recall_opt,
                                  recall_criterion, device)
        recall_sched.step()
        print(f"  Epoch {epoch:03d}/{recall_epochs} | Recall Loss: {loss:.4f}")
        if loss < best_recall_loss:
            best_recall_loss = loss
            torch.save(model.dual_tower.state_dict(),
                       os.path.join(save_dir, "recall_tower.pt"))
            print(f"    ✓ Saved recall checkpoint")

    # ── STAGE 2: Ranking ─────────────────────────────────────
    print("\n" + "═"*55)
    print("  STAGE 2 — Deep Interest Network Ranking")
    print("═"*55)
    ranking_criterion = RankingLoss()
    ranking_opt = AdamW(
        list(model.din.parameters()),
        lr=lr, weight_decay=weight_decay
    )
    ranking_sched = CosineAnnealingWarmRestarts(ranking_opt, T_0=ranking_epochs)

    best_ndcg = 0.0
    for epoch in range(1, ranking_epochs + 1):
        loss, auc, ndcg, hr = train_ranking_epoch(
            model, train_loader, ranking_opt, ranking_criterion, device
        )
        ranking_sched.step()
        print(
            f"  Epoch {epoch:03d}/{ranking_epochs} | "
            f"Loss: {loss:.4f} | CTR-AUC: {auc:.4f} | "
            f"NDCG@5: {ndcg:.4f} | HR@5: {hr:.4f}"
        )
        if ndcg > best_ndcg:
            best_ndcg = ndcg
            torch.save(model.din.state_dict(),
                       os.path.join(save_dir, "din_ranking.pt"))
            print(f"    ✓ Saved ranking checkpoint (NDCG@5={ndcg:.4f})")

    # ── STAGE 3: DQN Re-ranking ───────────────────────────────
    print("\n" + "═"*55)
    print("  STAGE 3 — Dueling DQN Re-ranking")
    print("═"*55)
    dqn_criterion = DQNLoss()
    dqn_opt = AdamW(
        list(model.dqn.parameters()),
        lr=lr * 0.5, weight_decay=weight_decay
    )
    replay_buffer = ReplayBuffer(capacity=20_000)

    # Pre-fill replay buffer từ synthetic data
    model.eval()
    with torch.no_grad():
        for batch in train_loader:
            batch = to_device(batch, device)
            u_emb = model.get_user_embedding(**build_user_batch(batch))
            ctx   = batch["context_feats"]
            state = torch.cat([u_emb, ctx], dim=-1).cpu()
            for i in range(len(state)):
                s    = state[i]
                a    = batch["dqn_action"][i].item()
                r    = batch["dqn_reward"][i].item()
                s_   = s + 0.01 * torch.randn_like(s)   # tiny noise → next state
                done = random.random() < 0.1
                replay_buffer.push(s, a, r, s_, float(done))
            if len(replay_buffer) > 10_000:
                break

    model.train()
    dqn_losses = []
    update_every = 4
    target_update_every = 100

    for step in range(1, dqn_steps + 1):
        if step % update_every == 0:
            loss_val = train_dqn_step(
                model, target_model, replay_buffer,
                dqn_opt, dqn_criterion, device, batch_size=64,
            )
            if loss_val is not None:
                dqn_losses.append(loss_val)

        if step % target_update_every == 0:
            soft_update_target(model, target_model, tau=0.005)

        if step % 500 == 0 and dqn_losses:
            avg = np.mean(dqn_losses[-100:])
            print(f"  Step {step:05d}/{dqn_steps} | DQN Loss (avg 100): {avg:.4f}")

    torch.save(model.dqn.state_dict(), os.path.join(save_dir, "dqn_rerank.pt"))
    print(f"  ✓ Saved DQN checkpoint")

    # Full model save
    torch.save({
        "model_state" : model.state_dict(),
        "cfg"         : vars(cfg),
        "best_ndcg"   : best_ndcg,
    }, os.path.join(save_dir, "full_pipeline.pt"))
    print(f"\n✅ Training complete. All checkpoints → {save_dir}/")
    return model


# ═══════════════════════════════════════════════════════════════
# 7. Load for inference
# ═══════════════════════════════════════════════════════════════

def load_model(checkpoint_path: str, device=None) -> CustomerBehaviorPipeline:
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt  = torch.load(checkpoint_path, map_location=device)
    cfg   = ModelConfig()
    for k, v in ckpt.get("cfg", {}).items():
        if hasattr(cfg, k) and not callable(getattr(cfg, k)):
            setattr(cfg, k, v)
    model = CustomerBehaviorPipeline(cfg).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    return model


if __name__ == "__main__":
    train(recall_epochs=5, ranking_epochs=8, dqn_steps=500,
          batch_size=32, n_train=2000, n_val=400)