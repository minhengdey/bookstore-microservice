from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class Attributes:
    data: Dict[str, Any] = field(default_factory=dict)

    def add(self, key: str, value: Any):
        self.data[key] = value

    def get(self, key: str) -> Any:
        return self.data.get(key)
        
    def to_dict(self):
        return self.data
