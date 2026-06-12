from django.db.models import Sum

from app.models import RecommendationLog, BehaviorEvent


class RecommenderRepository:
    def get_history(self, customer_id): return RecommendationLog.objects.filter(customer_id=customer_id)
    def save_log(self, customer_id, product_ids, strategy="collaborative"):
        return RecommendationLog.objects.create(customer_id=customer_id, product_ids=product_ids, strategy=strategy)

    def save_behavior(self, customer_id, product_id, action, action_weight=1.0, **kwargs):
        return BehaviorEvent.objects.create(
            customer_id=customer_id,
            product_id=product_id,
            action=action,
            action_weight=action_weight,
            **kwargs
        )

    def get_behavior_scores(self, customer_id):
        events = BehaviorEvent.objects.filter(customer_id=customer_id).values(
            "product_id", "action", "action_weight"
        )
        scores = {}
        for ev in events:
            pid = ev["product_id"]
            weight = float(ev.get("action_weight") or 1.0)
            scores[pid] = scores.get(pid, 0.0) + weight
        return scores

    def get_interacted_product_ids(self, customer_id: int) -> set[int]:
        return set(
            BehaviorEvent.objects.filter(customer_id=customer_id)
            .values_list("product_id", flat=True)
            .distinct()
        )

    def has_behavior_history(self, customer_id: int) -> bool:
        return BehaviorEvent.objects.filter(customer_id=customer_id).exists()

    def get_category_affinity(self, customer_id: int, catalog: dict[int, dict]) -> dict[int, float]:
        """Weighted category scores from user behavior events."""
        affinity: dict[int, float] = {}
        events = BehaviorEvent.objects.filter(customer_id=customer_id).values(
            "product_id", "action_weight"
        )
        for ev in events:
            meta = catalog.get(int(ev["product_id"]))
            if not meta:
                continue
            category_id = meta.get("category_id")
            if category_id is None:
                continue
            weight = float(ev.get("action_weight") or 1.0)
            cid = int(category_id)
            affinity[cid] = affinity.get(cid, 0.0) + weight
        return affinity

    def get_global_popularity_scores(self, active_product_ids: set[int]) -> dict[int, float]:
        """Normalized popularity from all users' behavior (cold-start baseline)."""
        if not active_product_ids:
            return {}

        rows = (
            BehaviorEvent.objects.filter(product_id__in=active_product_ids)
            .values("product_id")
            .annotate(total=Sum("action_weight"))
        )
        raw = {int(row["product_id"]): float(row["total"] or 0.0) for row in rows}
        max_score = max(raw.values()) if raw else 0.0
        if max_score <= 0:
            return {pid: 0.0 for pid in active_product_ids}
        return {pid: raw.get(pid, 0.0) / max_score for pid in active_product_ids}

    def get_cooccurrence_scores(
        self,
        customer_id: int,
        seed_product_ids: set[int],
        active_product_ids: set[int],
    ) -> dict[int, float]:
        """Products frequently interacted with by users who share seed products."""
        if not seed_product_ids:
            return {}

        peer_users = (
            BehaviorEvent.objects.filter(product_id__in=seed_product_ids)
            .exclude(customer_id=customer_id)
            .values_list("customer_id", flat=True)
            .distinct()
        )
        if not peer_users:
            return {}

        rows = (
            BehaviorEvent.objects.filter(customer_id__in=peer_users)
            .exclude(product_id__in=seed_product_ids)
            .values("product_id")
            .annotate(total=Sum("action_weight"))
            .order_by("-total")[:200]
        )
        return {
            int(row["product_id"]): float(row["total"] or 0.0)
            for row in rows
            if int(row["product_id"]) in active_product_ids
        }
