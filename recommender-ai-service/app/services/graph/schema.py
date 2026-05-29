from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass
class GraphNode:
    node_id: str
    node_type: str
    properties: Dict

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class GraphEdge:
    source: str
    target: str
    relation: str
    weight: float = 1.0
    properties: Dict | None = None

    def to_dict(self) -> Dict:
        data = asdict(self)
        if data["properties"] is None:
            data["properties"] = {}
        return data


def graph_snapshot(nodes: List[GraphNode], edges: List[GraphEdge]) -> Dict:
    return {
        "nodes": [n.to_dict() for n in nodes],
        "edges": [e.to_dict() for e in edges],
    }
