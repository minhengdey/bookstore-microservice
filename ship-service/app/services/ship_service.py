from datetime import date, timedelta
from app.repositories import ShippingRepository, ShippingMethodRepository


class ShippingService:
    def __init__(self):
        self.repo = ShippingRepository()
        self.method_repo = ShippingMethodRepository()

    def list(self): return self.repo.get_all()

    def get(self, pk):
        s = self.repo.get_by_id(pk)
        if not s: raise ValueError(f"Shipping {pk} not found")
        return s

    def list_methods(self): return self.method_repo.get_all()

    def create_shipment(self, order_id: int, method_id: int, address_data: dict):
        method = self.method_repo.get_by_id(method_id)
        if not method: raise ValueError(f"ShippingMethod {method_id} not found")
        shipping = self.repo.create(
            order_id=order_id,
            shipping_method=method,
            status="pending",
            estimated_delivery_date=date.today() + timedelta(days=5),
        )
        self.repo.set_address(shipping, **address_data)
        return self.repo.get_by_id(shipping.id)

    def update_status(self, pk, new_status):
        shipping = self.get(pk)
        return self.repo.update_status(shipping, new_status)
