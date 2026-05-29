import os, pickle
import pandas as pd
import networkx as nx
from collections import Counter

class RAGSystem:
    def __init__(self, G, df):
        self.G  = G
        self.df = df
        self._build_indexes()

    def _build_indexes(self):
        # product_id -> {name, category}
        self.products = (
            self.df[["product_id","product_name","category"]]
            .drop_duplicates("product_id")
            .set_index("product_id")
            .to_dict("index")
        )
        # category -> list of product_ids
        from collections import defaultdict
        self.cat_products = defaultdict(list)
        for pid, info in self.products.items():
            self.cat_products[info["category"]].append(pid)
            
        # --- ANTI-SUPER-NODE LOGIC ---
        # 1. Gán trọng số hành vi
        action_weights = {
            "purchase": 5.0, "add_to_cart": 3.0, "review": 2.0, "wishlist": 2.0,
            "click": 1.0, "view": 1.0, "search": 0.5, "remove_from_cart": -1.0
        }
        self.df["weight"] = self.df["action"].map(action_weights).fillna(1.0)
        
        # 2. Chuẩn hoá (Clip max 5.0 điểm mỗi user cho mỗi product)
        user_prod_scores = self.df.groupby(["user_id", "product_id"])["weight"].sum().clip(upper=5.0).reset_index()
        
        # 3. Tính điểm cá nhân hoá (Weighted Score)
        self.product_scores = user_prod_scores.groupby("product_id")["weight"].sum().to_dict()
        
        # 4. Xác định Super Nodes (Sản phẩm có tương tác vượt bách phân vị thứ 95)
        import numpy as np
        scores_array = np.array(list(self.product_scores.values()))
        if len(scores_array) > 0:
            threshold = np.percentile(scores_array, 95)
            self.super_nodes = {pid for pid, score in self.product_scores.items() if score > threshold}
        else:
            self.super_nodes = set()

    def retrieve_user_history(self, user_id, top_k=5):
        if user_id not in self.G: return []
        interactions = []
        for _, nbr, data in self.G.edges(user_id, data=True):
            if data.get("relation") == "PERFORMED":
                interactions.append({
                    "product_id": nbr,
                    "product_name": self.products.get(nbr, {}).get("product_name", nbr),
                    "category": self.products.get(nbr, {}).get("category", ""),
                    "action": data.get("action"),
                    "timestamp": data.get("timestamp"),
                })
        seen = set()
        unique = []
        for item in sorted(interactions, key=lambda x: x["timestamp"], reverse=True):
            if item["product_id"] not in seen:
                seen.add(item["product_id"])
                unique.append(item)
            if len(unique) >= top_k: break
        return unique

    def retrieve_popular_in_category(self, category, top_k=5):
        cat_data = self.df[self.df["category"] == category]
        if cat_data.empty: return []
        
        # Bỏ qua các Super Nodes, xếp hạng theo điểm trọng số (Weighted Score)
        candidates = []
        for pid in cat_data["product_id"].unique():
            if pid not in self.super_nodes:
                candidates.append((pid, self.product_scores.get(pid, 0)))
                
        # Sắp xếp giảm dần theo điểm
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        result = []
        for pid, score in candidates[:top_k]:
            p_info = self.products.get(pid, {})
            result.append({
                "product_id": pid,
                "product_name": p_info.get("product_name", ""),
                "category": p_info.get("category", ""),
                "interactions": round(score, 2),
            })
        return result

    def retrieve_similar_users(self, user_id, top_k=3):
        # Tính Node Similarity nhưng loại bỏ ảnh hưởng của Super Nodes
        user_products = set(
            nbr for _, nbr, d in self.G.edges(user_id, data=True)
            if d.get("action") in ("purchase", "add_to_cart") and nbr not in self.super_nodes
        )
        if not user_products: return []
        scores = {}
        for other in self.df["user_id"].unique():
            if other == user_id: continue
            other_products = set(
                nbr for _, nbr, d in self.G.edges(other, data=True)
                if d.get("action") in ("purchase", "add_to_cart") and nbr not in self.super_nodes
            )
            if not other_products: continue
            overlap = len(user_products & other_products)
            union   = len(user_products | other_products)
            scores[other] = overlap / union if union else 0
        return sorted(scores.items(), key=lambda x: -x[1])[:top_k]

    def recommend_products(self, user_id, top_k=5):
        history = self.retrieve_user_history(user_id, top_k=10)
        if not history:
            return {"user_id": user_id, "recommendations": [], "favorite_category": "unknown"}
        category_counts = Counter(h["category"] for h in history if h.get("category"))
        top_categories = [cat for cat, _ in category_counts.most_common(3)]
        fav_cat = top_categories[0] if top_categories else "unknown"
        seen_products = {h["product_id"] for h in history}

        # Diversify recommendations:
        # - 60% from the strongest category
        # - 30% from the next categories
        # - 10% exploration from any remaining categories
        primary_quota = max(1, int(round(top_k * 0.6)))
        secondary_quota = int(round(top_k * 0.3))
        if primary_quota + secondary_quota > top_k:
            secondary_quota = max(0, top_k - primary_quota)
        explore_quota = max(0, top_k - primary_quota - secondary_quota)

        selected = []
        selected_ids = set()

        def _append_products(products, limit):
            if limit <= 0:
                return 0
            added = 0
            for item in products:
                pid = item.get("product_id")
                if pid in seen_products or pid in selected_ids:
                    continue
                selected.append(item)
                selected_ids.add(pid)
                added += 1
                if added >= limit:
                    break
            return added

        # Primary category
        if top_categories:
            primary_pool = self.retrieve_popular_in_category(top_categories[0], top_k=30)
            _append_products(primary_pool, primary_quota)

        # Secondary categories (round-robin)
        if len(top_categories) > 1 and secondary_quota > 0:
            secondary_cats = top_categories[1:]
            cat_pools = {cat: self.retrieve_popular_in_category(cat, top_k=20) for cat in secondary_cats}
            idx = {cat: 0 for cat in secondary_cats}
            added_secondary = 0
            while added_secondary < secondary_quota:
                progressed = False
                for cat in secondary_cats:
                    pool = cat_pools[cat]
                    while idx[cat] < len(pool):
                        item = pool[idx[cat]]
                        idx[cat] += 1
                        pid = item.get("product_id")
                        if pid in seen_products or pid in selected_ids:
                            continue
                        selected.append(item)
                        selected_ids.add(pid)
                        added_secondary += 1
                        progressed = True
                        break
                    if added_secondary >= secondary_quota:
                        break
                if not progressed:
                    break

        # Exploration from all other categories
        if explore_quota > 0:
            fallback_categories = [c for c in self.cat_products.keys() if c not in top_categories]
            for cat in fallback_categories:
                if _append_products(self.retrieve_popular_in_category(cat, top_k=10), explore_quota) >= explore_quota:
                    break
                explore_quota = top_k - len(selected)
                if explore_quota <= 0:
                    break

        candidates = selected[:top_k]
        return {
            "user_id": user_id,
            "favorite_category": fav_cat,
            "recommendations": candidates,
        }
