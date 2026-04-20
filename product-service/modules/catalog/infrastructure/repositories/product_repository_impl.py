from typing import List, Optional
from ...domain.entities.product import Product
from ...domain.repositories.product_repository import ProductRepository
from ...domain.value_objects.money import Money
from ...domain.value_objects.sku import SKU
from ...domain.value_objects.attributes import Attributes
from ..models.product_model import ProductModel

class ProductRepositoryImpl(ProductRepository):
    def save(self, product: Product) -> Product:
        model_data = {
            "name": product.name,
            "category_id": product.category_id,
            "price": product.price.amount,
            "currency": product.price.currency,
            "sku": product.sku.value,
            "attributes": product.attributes.to_dict(),
            "description": product.description,
            "status": product.status,
        }
        
        if product.id:
            ProductModel.objects.filter(id=product.id).update(**model_data)
            return product
        else:
            model = ProductModel.objects.create(**model_data)
            product.id = model.id
            return product

    def get_by_id(self, product_id: int) -> Optional[Product]:
        try:
            model = ProductModel.objects.get(id=product_id)
            return self._to_entity(model)
        except ProductModel.DoesNotExist:
            return None

    def list_all(self) -> List[Product]:
        models = ProductModel.objects.all()
        return [self._to_entity(m) for m in models]

    def delete(self, product_id: int) -> None:
        ProductModel.objects.filter(id=product_id).delete()

    def _to_entity(self, model: ProductModel) -> Product:
        return Product(
            id=model.id,
            name=model.name,
            category_id=model.category_id,
            price=Money(amount=model.price, currency=model.currency),
            sku=SKU(value=model.sku),
            attributes=Attributes(data=model.attributes),
            description=model.description,
            status=model.status
        )
