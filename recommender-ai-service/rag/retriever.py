import os, pickle
import pandas as pd
import networkx as nx

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
        popular = (
            cat_data.groupby("product_id")
            .size().reset_index(name="interactions")
            .sort_values("interactions", ascending=False)
            .head(top_k)
        )
        result = []
        for _, row in popular.iterrows():
            p_info = self.products.get(row["product_id"], {})
            result.append({
                "product_id": row["product_id"],
                "product_name": p_info.get("product_name", ""),
                "category": p_info.get("category", ""),
                "interactions": row["interactions"],
            })
        return result

    def retrieve_similar_users(self, user_id, top_k=3):
        user_products = set(
            nbr for _, nbr, d in self.G.edges(user_id, data=True)
            if d.get("action") in ("purchase", "add_to_cart")
        )
        if not user_products: return []
        scores = {}
        for other in self.df["user_id"].unique():
            if other == user_id: continue
            other_products = set(
                nbr for _, nbr, d in self.G.edges(other, data=True)
                if d.get("action") in ("purchase", "add_to_cart")
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
        from collections import Counter
        fav_cat = Counter(h["category"] for h in history).most_common(1)[0][0]
        seen_products = {h["product_id"] for h in history}
        candidates = [
            p for p in self.retrieve_popular_in_category(fav_cat, top_k=20)
            if p["product_id"] not in seen_products
        ][:top_k]
        return {
            "user_id": user_id,
            "favorite_category": fav_cat,
            "recommendations": candidates,
        }
