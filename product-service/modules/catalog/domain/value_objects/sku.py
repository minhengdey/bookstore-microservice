from dataclasses import dataclass

@dataclass(frozen=True)
class SKU:
    value: str

    def __post_init__(self):
        if not self.value or len(self.value) < 3:
            raise ValueError("Invalid SKU")
