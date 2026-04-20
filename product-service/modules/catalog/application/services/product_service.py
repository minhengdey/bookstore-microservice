from typing import List, Optional
from ...domain.entities.product import Product
from ...domain.repositories.product_repository import ProductRepository
from ...domain.value_objects.money import Money
from ...domain.value_objects.sku import SKU

class ProductApplicationService:
    def __init__(self, repository: ProductRepository):
        self.repository = repository

    def create_product(self, name: str, category_id: int, price_amount: float, sku_value: str, attributes_data: dict, description: str = "") -> Product:
        product = Product(
            id=None,
            name=name,
            category_id=category_id,
            price=Money(amount=price_amount),
            sku=SKU(value=sku_value),
            description=description
        )
        for k, v in attributes_data.items():
            product.set_attribute(k, v)
            
        return self.repository.save(product)

    def get_product(self, product_id: int) -> Optional[Product]:
        return self.repository.get_by_id(product_id)

    def list_products(self) -> List[Product]:
        return self.repository.list_all()

    def delete_product(self, product_id: int) -> None:
        self.repository.delete(product_id)
