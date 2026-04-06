"""
model_behavior.py  (v2 — Production-grade)
-------------------------------------------
Kiến trúc nâng cấp dựa trên báo cáo kỹ thuật e-commerce:

1. Dual-Tower (Two-Tower) Model
   - User Tower  : embedding + LSTM sequence encoder
   - Item Tower  : embedding + feature encoder
   - Dot-product similarity → Recall stage

2. Deep Interest Network (DIN) — Ranking stage
   - Attention mechanism trên purchase/browsing history
   - Tập trung vào items liên quan đến target item
   - CTR / CVR prediction

3. Dueling DQN head — Re-ranking / Dynamic Pricing stage
   - State: user embedding + context features
   - Value head V(s) + Advantage head A(s, a)
   - Tránh overestimation như báo cáo đề xuất

4. Multi-task output
   - Classification head (service category)
   - Recommendation scores
   - CTR head

References từ báo cáo:
  - Multi-stage: Recall → Ranking → Re-ranking
  - DNN + Attention cho CTR/CVR
  - Dueling DQN tránh overestimation
  - ANN/HNSW cho Recall stage (kết hợp với FAISS ở vector_store.py)
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F


# ═══════════════════════════════════════════════════════════════
# 0. Config
# ═══════════════════════════════════════════════════════════════

class ModelConfig:
    """Tất cả hyperparameter tập trung tại đây."""

    # Vocabulary sizes
    num_users           : int = 5000
    num_items           : int = 2000     # unique items trong history
    num_services        : int = 20       # service trong catalogue
    num_service_categories: int = 5
    num_locations       : int = 100

    # Embedding dims
    user_embed_dim      : int = 64
    item_embed_dim      : int = 64       # shared giữa các towers
    location_embed_dim  : int = 32

    # Sequence encoder
    lstm_hidden_dim     : int = 128
    lstm_layers         : int = 2
    lstm_dropout        : float = 0.3

    # Attention (DIN)
    attention_hidden    : int = 64

    # MLP dims
    user_tower_dims     : list = None
    ranking_mlp_dims    : list = None
    mlp_dropout         : float = 0.4

    # DQN
    num_actions         : int = 3        # tăng / giữ / giảm giá

    def __init__(self):
        self.user_tower_dims  = [256, 128, 64]
        self.ranking_mlp_dims = [512, 256, 128, 64]


# ═══════════════════════════════════════════════════════════════
# 1. Building Blocks
# ═══════════════════════════════════════════════════════════════

class MLP(nn.Module):
    """Configurable MLP với BatchNorm, GELU, Dropout."""

    def __init__(self, in_dim: int, hidden_dims: list,
                 dropout: float = 0.4, use_bn: bool = True):
        super().__init__()
        layers = []
        prev = in_dim
        for h in hidden_dims:
            layers.append(nn.Linear(prev, h))
            if use_bn:
                layers.append(nn.BatchNorm1d(h))
            layers.append(nn.GELU())
            layers.append(nn.Dropout(dropout))
            prev = h
        self.net   = nn.Sequential(*layers)
        self.out_dim = prev

    def forward(self, x):
        return self.net(x)


class LSTMEncoder(nn.Module):
    """
    Encode chuỗi item history → fixed-size vector.
    Dùng pack_padded_sequence để xử lý padding đúng cách.
    """

    def __init__(self, num_items: int, embed_dim: int,
                 hidden_dim: int, num_layers: int, dropout: float):
        super().__init__()
        self.embedding = nn.Embedding(num_items + 1, embed_dim, padding_idx=0)
        self.lstm = nn.LSTM(
            embed_dim, hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
            bidirectional=True,      # bidirectional → 2× hidden
        )
        self.proj     = nn.Linear(hidden_dim * 2, hidden_dim)  # project về hidden_dim
        self.layer_norm = nn.LayerNorm(hidden_dim)
        self.out_dim  = hidden_dim

    def forward(self, ids: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        """
        Args:
            ids     : (B, T) padded item indices
            lengths : (B,)   true lengths
        Returns:
            (B, hidden_dim)
        """
        emb    = self.embedding(ids)                          # (B, T, E)
        packed = nn.utils.rnn.pack_padded_sequence(
            emb, lengths.cpu(), batch_first=True, enforce_sorted=False
        )
        out, _ = self.lstm(packed)
        out, _ = nn.utils.rnn.pad_packed_sequence(out, batch_first=True)  # (B, T, 2H)

        # Lấy hidden state tại vị trí cuối mỗi sequence
        idx = (lengths - 1).clamp(min=0).unsqueeze(1).unsqueeze(2)  # (B,1,1)
        idx = idx.expand(-1, 1, out.size(2))
        last = out.gather(1, idx).squeeze(1)                         # (B, 2H)

        h = self.proj(last)                                           # (B, H)
        return self.layer_norm(h)


class TargetAttention(nn.Module):
    """
    Deep Interest Network (DIN) Attention:
    Tính attention weight của mỗi item trong lịch sử
    so với target item (query).

    Công thức:
        e_i = MLP([h_i ⊕ q ⊕ h_i*q ⊕ |h_i - q|])
        α_i = softmax(e_i)
        out = Σ α_i * h_i
    """

    def __init__(self, item_dim: int, hidden_dim: int):
        super().__init__()
        # 4 interaction features: concat, hadamard, diff + query
        self.attn_mlp = MLP(
            in_dim       = item_dim * 4,
            hidden_dims  = [hidden_dim, hidden_dim // 2, 1],
            dropout      = 0.1,
            use_bn       = False,
        )

    def forward(
        self,
        history_emb : torch.Tensor,   # (B, T, D)
        target_emb  : torch.Tensor,   # (B, D)
        mask        : torch.Tensor,   # (B, T) boolean — True for padding
    ) -> torch.Tensor:
        """Returns (B, D) — attention-weighted history."""
        B, T, D = history_emb.shape
        q = target_emb.unsqueeze(1).expand(-1, T, -1)    # (B, T, D)

        # Interaction features
        concat   = torch.cat([history_emb, q], dim=-1)   # (B, T, 2D)
        hadamard = history_emb * q                         # (B, T, D)
        diff     = (history_emb - q).abs()                 # (B, T, D)
        feat     = torch.cat([concat, hadamard, diff], dim=-1)  # (B, T, 4D)

        # Attention score
        score = self.attn_mlp(feat.view(B * T, -1)).view(B, T)   # (B, T)
        score = score.masked_fill(mask, float("-inf"))             # mask padding
        weight = F.softmax(score, dim=-1)                          # (B, T)

        # Weighted sum
        out = (weight.unsqueeze(-1) * history_emb).sum(dim=1)     # (B, D)
        return out


# ═══════════════════════════════════════════════════════════════
# 2. Recall Stage — Dual-Tower Model
#    Dùng trong giai đoạn Recall để retrieve candidates nhanh
#    (tương tự ANN/HNSW trong báo cáo)
# ═══════════════════════════════════════════════════════════════

class UserTower(nn.Module):
    """
    Encode user → dense embedding vector.
    Được index vào FAISS ở inference time.
    """

    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.user_embed    = nn.Embedding(cfg.num_users + 1,     cfg.user_embed_dim)
        self.location_embed= nn.Embedding(cfg.num_locations + 1, cfg.location_embed_dim)

        self.purchase_enc  = LSTMEncoder(
            cfg.num_items, cfg.item_embed_dim,
            cfg.lstm_hidden_dim, cfg.lstm_layers, cfg.lstm_dropout,
        )
        self.browsing_enc  = LSTMEncoder(
            cfg.num_items, cfg.item_embed_dim,
            cfg.lstm_hidden_dim, cfg.lstm_layers, cfg.lstm_dropout,
        )

        raw_dim = (
            cfg.user_embed_dim + cfg.location_embed_dim
            + 2                                 # age, gender
            + cfg.lstm_hidden_dim * 2           # purchase + browsing
        )
        self.mlp     = MLP(raw_dim, cfg.user_tower_dims, cfg.mlp_dropout)
        self.out_dim = cfg.user_tower_dims[-1]

    def forward(self, user_ids, ages, genders, location_ids,
                purchase_ids, purchase_lens,
                browsing_ids,  browsing_lens):
        u  = self.user_embed(user_ids)
        l  = self.location_embed(location_ids)
        p  = self.purchase_enc(purchase_ids, purchase_lens)
        b  = self.browsing_enc(browsing_ids,  browsing_lens)

        x  = torch.cat([u, l, ages, genders, p, b], dim=-1)
        return F.normalize(self.mlp(x), dim=-1)   # L2 normalize → cosine via dot


class ServiceTower(nn.Module):
    """
    Encode service → dense embedding vector.
    Được pre-compute và lưu vào FAISS.
    """

    def __init__(self, cfg: ModelConfig, service_feature_dim: int = 32):
        super().__init__()
        self.service_embed = nn.Embedding(cfg.num_services + 1, cfg.item_embed_dim)
        self.category_embed= nn.Embedding(cfg.num_service_categories + 1, 16)

        raw_dim = cfg.item_embed_dim + 16 + service_feature_dim
        self.mlp = MLP(raw_dim, [128, cfg.user_tower_dims[-1]], dropout=0.2)
        self.out_dim = cfg.user_tower_dims[-1]

    def forward(self, service_ids, category_ids, service_features):
        """
        service_ids      : (B,)
        category_ids     : (B,)
        service_features : (B, service_feature_dim) — price, tags, etc.
        """
        s = self.service_embed(service_ids)
        c = self.category_embed(category_ids)
        x = torch.cat([s, c, service_features], dim=-1)
        return F.normalize(self.mlp(x), dim=-1)


class DualTowerModel(nn.Module):
    """
    Two-Tower model cho Recall stage.
    Similarity = dot product của L2-normalized vectors.
    """

    def __init__(self, cfg: ModelConfig, service_feature_dim: int = 32):
        super().__init__()
        self.user_tower    = UserTower(cfg)
        self.service_tower = ServiceTower(cfg, service_feature_dim)
        self.temperature   = nn.Parameter(torch.tensor(0.07))   # learnable temperature

    def forward(self, user_batch: dict, service_batch: dict):
        u_vec = self.user_tower(**user_batch)      # (B, D)
        s_vec = self.service_tower(**service_batch) # (B, D)
        # Scaled cosine similarity (InfoNCE style)
        logits = torch.matmul(u_vec, s_vec.T) / self.temperature.clamp(min=0.01)
        return logits, u_vec, s_vec


# ═══════════════════════════════════════════════════════════════
# 3. Ranking Stage — Deep Interest Network (DIN)
#    Ranking candidates sau Recall với CTR/CVR prediction
# ═══════════════════════════════════════════════════════════════

class DeepInterestNetwork(nn.Module):
    """
    DIN model cho Ranking stage.

    Input:
      - User embedding (from UserTower)
      - Target service embedding
      - Purchase history với Attention trên target
      - Browsing history với Attention trên target
      - Context features (time, location, etc.)

    Output:
      - CTR logit (xác suất click)
      - CVR logit (xác suất convert)
      - Category logit (service category)
      - Service scores (recommendation)
    """

    def __init__(self, cfg: ModelConfig):
        super().__init__()
        # History embeddings (shared weights với LSTMEncoder — hiệu quả hơn)
        self.item_embed     = nn.Embedding(cfg.num_items + 1, cfg.item_embed_dim, padding_idx=0)
        self.service_embed  = nn.Embedding(cfg.num_services + 1, cfg.item_embed_dim)

        # DIN Attention (target-aware)
        self.purchase_attn  = TargetAttention(cfg.item_embed_dim, cfg.attention_hidden)
        self.browsing_attn  = TargetAttention(cfg.item_embed_dim, cfg.attention_hidden)

        # Fused dim: user_emb + target_svc_emb + attn_purchase + attn_browsing + context
        context_dim  = 8     # one-hot time-of-day buckets, day-of-week
        fused_dim = (
            cfg.user_tower_dims[-1]  # user tower output
            + cfg.item_embed_dim     # target service
            + cfg.item_embed_dim     # attended purchase
            + cfg.item_embed_dim     # attended browsing
            + context_dim
        )

        self.ranking_mlp = MLP(fused_dim, cfg.ranking_mlp_dims, cfg.mlp_dropout)
        final_dim        = cfg.ranking_mlp_dims[-1]

        # Output heads
        self.ctr_head      = nn.Linear(final_dim, 1)
        self.cvr_head      = nn.Linear(final_dim, 1)
        self.category_head = nn.Linear(final_dim, cfg.num_service_categories)
        self.service_head  = nn.Linear(final_dim, cfg.num_services)

    def forward(
        self,
        user_emb       : torch.Tensor,   # (B, D_u) from UserTower
        target_ids     : torch.Tensor,   # (B,) target service id
        purchase_ids   : torch.Tensor,   # (B, T_p)
        purchase_lens  : torch.Tensor,   # (B,)
        browsing_ids   : torch.Tensor,   # (B, T_b)
        browsing_lens  : torch.Tensor,   # (B,)
        context_feats  : torch.Tensor,   # (B, context_dim)
    ):
        B, T_p = purchase_ids.shape
        T_b    = browsing_ids.shape[1]

        # Target embedding
        target_emb = self.service_embed(target_ids)              # (B, E)

        # History embeddings
        p_hist = self.item_embed(purchase_ids)                   # (B, T_p, E)
        b_hist = self.item_embed(browsing_ids)                   # (B, T_b, E)

        # Padding masks (True = padding)
        p_mask = torch.arange(T_p, device=purchase_ids.device).unsqueeze(0) \
                 >= purchase_lens.unsqueeze(1)                   # (B, T_p)
        b_mask = torch.arange(T_b, device=browsing_ids.device).unsqueeze(0) \
                 >= browsing_lens.unsqueeze(1)                   # (B, T_b)

        # DIN Attention
        p_attn = self.purchase_attn(p_hist, target_emb, p_mask) # (B, E)
        b_attn = self.browsing_attn(b_hist, target_emb, b_mask) # (B, E)

        # Fusion
        fused = torch.cat([user_emb, target_emb, p_attn, b_attn, context_feats], dim=-1)
        h     = self.ranking_mlp(fused)

        # Outputs
        ctr_logit   = self.ctr_head(h).squeeze(-1)              # (B,)
        cvr_logit   = self.cvr_head(h).squeeze(-1)              # (B,)
        cat_logits  = self.category_head(h)                     # (B, C)
        svc_scores  = self.service_head(h)                      # (B, S)

        return ctr_logit, cvr_logit, cat_logits, svc_scores


# ═══════════════════════════════════════════════════════════════
# 4. Re-ranking / Pricing Stage — Dueling DQN
#    Như báo cáo đề xuất để tránh overestimation
# ═══════════════════════════════════════════════════════════════

class DuelingDQN(nn.Module):
    """
    Dueling DQN cho Re-ranking và Dynamic Pricing.

    Kiến trúc Dueling tách biệt:
      - V(s)    : giá trị của trạng thái (state value)
      - A(s, a) : lợi thế của từng hành động (advantage)
      - Q(s, a) = V(s) + A(s, a) - mean(A(s, .))

    State = user embedding + context + ranked service scores
    Action = tăng/giữ/giảm giá (hoặc re-rank order)
    """

    def __init__(self, state_dim: int, num_actions: int,
                 hidden_dims: list = None):
        super().__init__()
        hidden_dims = hidden_dims or [256, 128]

        # Shared encoder
        self.shared = MLP(state_dim, hidden_dims, dropout=0.3)
        shared_out  = hidden_dims[-1]

        # Value stream V(s): scalar
        self.value_stream = nn.Sequential(
            nn.Linear(shared_out, 64),
            nn.GELU(),
            nn.Linear(64, 1),
        )

        # Advantage stream A(s, a): per-action
        self.advantage_stream = nn.Sequential(
            nn.Linear(shared_out, 64),
            nn.GELU(),
            nn.Linear(64, num_actions),
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """
        Args:
            state : (B, state_dim)
        Returns:
            Q     : (B, num_actions)
        """
        h = self.shared(state)
        V = self.value_stream(h)          # (B, 1)
        A = self.advantage_stream(h)      # (B, num_actions)

        # Q = V + (A - mean(A))  ← Dueling formula
        Q = V + (A - A.mean(dim=-1, keepdim=True))
        return Q


# ═══════════════════════════════════════════════════════════════
# 5. Full Pipeline Model
#    Tích hợp 3 stage: Recall → Ranking → Re-ranking
# ═══════════════════════════════════════════════════════════════

class CustomerBehaviorPipeline(nn.Module):
    """
    Multi-stage recommendation pipeline:

    Stage 1 (Recall)     : DualTowerModel — fast ANN retrieval
    Stage 2 (Ranking)    : DeepInterestNetwork — CTR/CVR + service scores
    Stage 3 (Re-ranking) : DuelingDQN — price optimization / reorder

    Trong production:
      - Stage 1 chạy offline → pre-compute user/item embeddings → FAISS
      - Stage 2 chạy online → re-score top-k candidates
      - Stage 3 chạy online → final business optimization
    """

    def __init__(self, cfg: ModelConfig, service_feature_dim: int = 32):
        super().__init__()
        self.cfg = cfg

        # Stage 1
        self.dual_tower = DualTowerModel(cfg, service_feature_dim)

        # Stage 2
        self.din = DeepInterestNetwork(cfg)

        # Stage 3
        state_dim = cfg.user_tower_dims[-1] + 8  # user_emb + context
        self.dqn  = DuelingDQN(state_dim, cfg.num_actions, [128, 64])

    def forward_recall(self, user_batch: dict, service_batch: dict):
        """Stage 1: Recall — trả về similarity logits."""
        return self.dual_tower(user_batch, service_batch)

    def forward_ranking(
        self,
        user_emb       : torch.Tensor,
        target_ids     : torch.Tensor,
        purchase_ids   : torch.Tensor,
        purchase_lens  : torch.Tensor,
        browsing_ids   : torch.Tensor,
        browsing_lens  : torch.Tensor,
        context_feats  : torch.Tensor,
    ):
        """Stage 2: Ranking — CTR/CVR và service scores."""
        return self.din(
            user_emb, target_ids,
            purchase_ids, purchase_lens,
            browsing_ids,  browsing_lens,
            context_feats,
        )

    def forward_reranking(self, user_emb: torch.Tensor,
                          context_feats: torch.Tensor) -> torch.Tensor:
        """Stage 3: Re-ranking / Pricing — Q-values."""
        state = torch.cat([user_emb, context_feats], dim=-1)
        return self.dqn(state)

    def get_user_embedding(
        self,
        user_ids, ages, genders, location_ids,
        purchase_ids, purchase_lens,
        browsing_ids,  browsing_lens,
    ) -> torch.Tensor:
        """Tiện ích: lấy user embedding từ UserTower."""
        return self.dual_tower.user_tower(
            user_ids, ages, genders, location_ids,
            purchase_ids, purchase_lens,
            browsing_ids,  browsing_lens,
        )


# ═══════════════════════════════════════════════════════════════
# 6. Loss Functions
# ═══════════════════════════════════════════════════════════════

class RecallLoss(nn.Module):
    """
    InfoNCE (in-batch negatives) loss cho Two-Tower training.
    Trong một batch, các sample không match nhau là negative.
    """

    def __init__(self):
        super().__init__()

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        """
        logits : (B, B) — similarity matrix (diagonal = positives)
        """
        B = logits.size(0)
        labels = torch.arange(B, device=logits.device)
        # Symmetric loss (user→item + item→user)
        l1 = F.cross_entropy(logits,   labels)
        l2 = F.cross_entropy(logits.T, labels)
        return (l1 + l2) / 2


class RankingLoss(nn.Module):
    """
    Multi-task loss cho DIN Ranking stage.
    Kết hợp: CTR + CVR + Category + Recommendation
    """

    def __init__(self, w_ctr=1.0, w_cvr=0.5, w_cat=0.3, w_rec=0.4):
        super().__init__()
        self.w_ctr = w_ctr
        self.w_cvr = w_cvr
        self.w_cat = w_cat
        self.w_rec = w_rec

    def forward(
        self,
        ctr_logit  : torch.Tensor,   # (B,)
        cvr_logit  : torch.Tensor,   # (B,)
        cat_logits : torch.Tensor,   # (B, C)
        svc_scores : torch.Tensor,   # (B, S)
        ctr_label  : torch.Tensor,   # (B,) binary
        cvr_label  : torch.Tensor,   # (B,) binary
        cat_label  : torch.Tensor,   # (B,) long
        svc_label  : torch.Tensor,   # (B, S) multi-hot
    ):
        l_ctr = F.binary_cross_entropy_with_logits(ctr_logit, ctr_label.float())
        l_cvr = F.binary_cross_entropy_with_logits(cvr_logit, cvr_label.float())
        l_cat = F.cross_entropy(cat_logits, cat_label)
        l_rec = F.binary_cross_entropy_with_logits(svc_scores, svc_label.float())

        total = (self.w_ctr * l_ctr + self.w_cvr * l_cvr
                 + self.w_cat * l_cat + self.w_rec * l_rec)
        return total, {"ctr": l_ctr, "cvr": l_cvr, "cat": l_cat, "rec": l_rec}


class DQNLoss(nn.Module):
    """
    Huber loss cho Dueling DQN (ổn định hơn MSE với outliers).
    """

    def __init__(self):
        super().__init__()

    def forward(
        self,
        q_pred   : torch.Tensor,   # (B, A)
        actions  : torch.Tensor,   # (B,)  — action taken
        targets  : torch.Tensor,   # (B,)  — TD target
    ) -> torch.Tensor:
        q_taken = q_pred.gather(1, actions.unsqueeze(1)).squeeze(1)  # (B,)
        return F.huber_loss(q_taken, targets)


# ═══════════════════════════════════════════════════════════════
# 7. Smoke Test
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    cfg = ModelConfig()
    model = CustomerBehaviorPipeline(cfg)
    print(model)

    B, T = 8, 12
    CONTEXT_DIM = 8
    SVC_FEAT_DIM = 32

    # Dummy user batch
    user_batch = dict(
        user_ids      = torch.randint(1, cfg.num_users,    (B,)),
        ages          = torch.rand(B, 1),
        genders       = torch.randint(0, 2, (B, 1)).float(),
        location_ids  = torch.randint(1, cfg.num_locations, (B,)),
        purchase_ids  = torch.randint(1, cfg.num_items, (B, T)),
        purchase_lens = torch.full((B,), T),
        browsing_ids  = torch.randint(1, cfg.num_items, (B, T)),
        browsing_lens = torch.full((B,), T),
    )

    # Dummy service batch
    svc_batch = dict(
        service_ids      = torch.randint(1, cfg.num_services, (B,)),
        category_ids     = torch.randint(0, cfg.num_service_categories, (B,)),
        service_features = torch.rand(B, SVC_FEAT_DIM),
    )

    context = torch.rand(B, CONTEXT_DIM)

    # Stage 1: Recall
    logits, u_vec, s_vec = model.forward_recall(user_batch, svc_batch)
    print(f"[Recall]   logits: {logits.shape}, user_emb: {u_vec.shape}")

    # Stage 2: Ranking
    ctr, cvr, cat, svc = model.forward_ranking(
        u_vec,
        torch.randint(1, cfg.num_services, (B,)),
        user_batch["purchase_ids"], user_batch["purchase_lens"],
        user_batch["browsing_ids"],  user_batch["browsing_lens"],
        context,
    )
    print(f"[Ranking]  CTR: {ctr.shape}, CVR: {cvr.shape}, "
          f"Category: {cat.shape}, Services: {svc.shape}")

    # Stage 3: Re-ranking
    q_vals = model.forward_reranking(u_vec, context)
    print(f"[DQN]      Q-values: {q_vals.shape}")

    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\nTotal trainable params: {n_params:,}")