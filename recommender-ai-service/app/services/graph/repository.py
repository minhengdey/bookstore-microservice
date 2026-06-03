import json
import os
from pathlib import Path
from typing import Dict, List

from .schema import GraphEdge, GraphNode, graph_snapshot


class GraphRepository:
    """
    Lightweight graph store for recommender runtime.
    Data is persisted to JSON to keep dev setup simple.
    """

    def __init__(self, graph_path: str | None = None):
        default_path = Path(__file__).resolve().parents[3] / "data" / "graph_kb.json"
        self.graph_path = Path(graph_path or os.environ.get("GRAPH_KB_PATH", str(default_path)))
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)

    def append_behavior(
        self,
        customer_id: int,
        product_id: int,
        action: str,
        action_weight: float,
        category_id: int | None = None,
    ) -> None:
        data = self._load()
        nodes = data["nodes"]
        edges = data["edges"]

        u = f"user:{customer_id}"
        p = f"product:{product_id}"

        self._upsert_node(nodes, GraphNode(u, "User", {"customer_id": customer_id}))
        self._upsert_node(nodes, GraphNode(p, "Product", {"product_id": product_id}))

        if category_id is not None:
            c = f"category:{category_id}"
            self._upsert_node(nodes, GraphNode(c, "Category", {"category_id": category_id}))
            self._upsert_edge(edges, GraphEdge(p, c, "BELONGS_TO", 1.0, {}))

        self._upsert_edge(
            edges,
            GraphEdge(
                source=u,
                target=p,
                relation=action.upper(),
                weight=float(action_weight),
                properties={"action": action},
            ),
        )
        self._save(data)

    def top_neighbor_products(self, customer_id: int, top_k: int = 20) -> Dict[int, float]:
        data = self._load()
        user_node = f"user:{customer_id}"
        product_scores: Dict[int, float] = {}
        for e in data["edges"]:
            if e.get("source") != user_node:
                continue
            if not str(e.get("target", "")).startswith("product:"):
                continue
            try:
                bid = int(str(e["target"]).split(":")[1])
            except Exception:
                continue
            product_scores[bid] = product_scores.get(bid, 0.0) + float(e.get("weight") or 0.0)

        ranked = sorted(product_scores.items(), key=lambda kv: kv[1], reverse=True)
        return dict(ranked[:top_k])

    def explain(self, customer_id: int, product_id: int) -> str:
        score = self.top_neighbor_products(customer_id, top_k=100).get(product_id, 0.0)
        if score <= 0:
            return "graph: no direct behavior edge"
        return f"graph: direct behavior weight={score:.2f}"

    def get_snapshot(self) -> Dict:
        return self._load()

    def _load(self) -> Dict:
        if not self.graph_path.exists():
            return graph_snapshot([], [])
        try:
            return json.loads(self.graph_path.read_text(encoding="utf-8"))
        except Exception:
            return graph_snapshot([], [])

    def _save(self, payload: Dict) -> None:
        self.graph_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _upsert_node(nodes: List[Dict], node: GraphNode) -> None:
        for n in nodes:
            if n.get("node_id") == node.node_id:
                n["properties"] = {**(n.get("properties") or {}), **node.properties}
                return
        nodes.append(node.to_dict())

    @staticmethod
    def _upsert_edge(edges: List[Dict], edge: GraphEdge) -> None:
        for e in edges:
            if (
                e.get("source") == edge.source
                and e.get("target") == edge.target
                and e.get("relation") == edge.relation
            ):
                e["weight"] = float(e.get("weight") or 0.0) + float(edge.weight)
                return
        edges.append(edge.to_dict())
