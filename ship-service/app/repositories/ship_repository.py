from app.models import Shipping, ShippingAddress, ShippingStatus, ShippingMethod, ShippingFeature


class ShippingMethodRepository:
    def get_all(self): return ShippingMethod.objects.prefetch_related("features").all()
    def get_by_id(self, pk): return ShippingMethod.objects.filter(pk=pk).first()
    def create(self, **kw): return ShippingMethod.objects.create(**kw)


class ShippingRepository:
    def get_all(self): return Shipping.objects.select_related("shipping_method", "address").all()
    def get_by_id(self, pk): return Shipping.objects.select_related("shipping_method", "address").filter(pk=pk).first()
    def get_by_order(self, order_id): return Shipping.objects.filter(order_id=order_id).first()
    def create(self, **kw): return Shipping.objects.create(**kw)
    def update_status(self, shipping, new_status):
        shipping.status = new_status
        shipping.save(update_fields=["status"])
        ShippingStatus.objects.create(shipping=shipping, status=new_status)
        return shipping
    def set_address(self, shipping, **kw):
        addr, _ = ShippingAddress.objects.update_or_create(shipping=shipping, defaults=kw)
        return addr
