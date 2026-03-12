from app.models import (
    Warehouse, WarehouseLocation, Inventory,
    Supplier, PurchaseOrder, PurchaseOrderItem,
    StockMovement, StockMovementLog, StockTransfer,
)


class WarehouseRepository:
    def get_all(self): return Warehouse.objects.prefetch_related("locations").all()
    def get_by_id(self, pk): return Warehouse.objects.filter(pk=pk).first()
    def create(self, **kw): return Warehouse.objects.create(**kw)
    def update(self, obj, **kw):
        for k, v in kw.items(): setattr(obj, k, v)
        obj.save(); return obj
    def delete(self, obj): obj.delete()
    def add_location(self, warehouse, **kw): return WarehouseLocation.objects.create(warehouse=warehouse, **kw)


class InventoryRepository:
    def get_all(self): return Inventory.objects.select_related("warehouse").all()
    def get_by_id(self, pk): return Inventory.objects.filter(pk=pk).first()
    def get_by_book(self, book_id): return Inventory.objects.filter(book_id=book_id)
    def get_by_warehouse(self, warehouse_id): return Inventory.objects.filter(warehouse_id=warehouse_id)
    def create(self, **kw): return Inventory.objects.create(**kw)
    def update_stock(self, inv, delta: int):
        inv.stock_quantity = max(0, inv.stock_quantity + delta)
        inv.save(update_fields=["stock_quantity", "last_updated"]); return inv


class SupplierRepository:
    def get_all(self): return Supplier.objects.all()
    def get_by_id(self, pk): return Supplier.objects.filter(pk=pk).first()
    def create(self, **kw): return Supplier.objects.create(**kw)
    def update(self, obj, **kw):
        for k, v in kw.items(): setattr(obj, k, v)
        obj.save(); return obj
    def delete(self, obj): obj.delete()


class PurchaseOrderRepository:
    def get_all(self): return PurchaseOrder.objects.select_related("supplier").prefetch_related("items").all()
    def get_by_id(self, pk): return PurchaseOrder.objects.select_related("supplier").prefetch_related("items").filter(pk=pk).first()
    def create(self, supplier, **kw): return PurchaseOrder.objects.create(supplier=supplier, **kw)
    def add_item(self, po, **kw): return PurchaseOrderItem.objects.create(purchase_order=po, **kw)
    def update_status(self, po, status): po.status = status; po.save(update_fields=["status"]); return po


class StockMovementRepository:
    def get_all(self): return StockMovement.objects.all()
    def create(self, **kw): return StockMovement.objects.create(**kw)
    def add_log(self, movement, action, description=""):
        return StockMovementLog.objects.create(movement=movement, action=action, description=description)
    def create_transfer(self, **kw): return StockTransfer.objects.create(**kw)
