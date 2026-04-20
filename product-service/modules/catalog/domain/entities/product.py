from dataclasses import dataclass, field
from typing import List, Optional
from ..value_objects.money import Money
from ..value_objects.sku import SKU
from ..value_objects.attributes import Attributes

@dataclass
class Product:
    id: Optional[int]
    name: str
    category_id: int
    price: Money
    sku: SKU
    attributes: Attributes = field(default_factory=Attributes)
    description: str = ""
    status: str = "active"
    
    def update_price(self, new_price: Money):
        self.price = new_price
        
    def set_attribute(self, key: str, value: any):
        self.attributes.add(key, value)
