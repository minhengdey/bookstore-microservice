from abc import ABC, abstractmethod
from typing import List, Optional
from ..entities.product import Product

class ProductRepository(ABC):
    @abstractmethod
    def save(self, product: Product) -> Product:
        pass

    @abstractmethod
    def get_by_id(self, product_id: int) -> Optional[Product]:
        pass

    @abstractmethod
    def list_all(self) -> List[Product]:
        pass

    @abstractmethod
    def delete(self, product_id: int) -> None:
        pass
