from app.models import Order, OrderItem, OrderDiscount, Discount, Invoice


class OrderRepository:
    def get_all(self): return Order.objects.prefetch_related("items", "order_discounts").all()
    def get_by_id(self, pk): return Order.objects.prefetch_related("items", "order_discounts").filter(pk=pk).first()
    def get_by_customer(self, customer_id): return Order.objects.filter(customer_id=customer_id)
    def create(self, **kw): return Order.objects.create(**kw)
    def add_item(self, order, **kw): return OrderItem.objects.create(order=order, **kw)
    def update_status(self, order, new_status): order.status = new_status; order.save(update_fields=["status"]); return order
    def update_total(self, order, total): order.total_amount = total; order.save(update_fields=["total_amount"]); return order
    def create_invoice(self, order, **kw): return Invoice.objects.create(order=order, **kw)
    def apply_discount(self, order, discount_id, applied_value):
        return OrderDiscount.objects.create(order=order, discount_id=discount_id, applied_value=applied_value)


class DiscountRepository:
    def get_all(self): return Discount.objects.all()
    def get_by_id(self, pk): return Discount.objects.filter(pk=pk).first()
    def get_by_code(self, code): return Discount.objects.filter(discount_code=code, is_active=True).first()
    def create(self, **kw): return Discount.objects.create(**kw)
    def update(self, obj, **kw):
        for k, v in kw.items(): setattr(obj, k, v)
        obj.save(); return obj
