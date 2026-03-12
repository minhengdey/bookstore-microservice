from app.repositories import (
    WarehouseRepository, InventoryRepository,
    SupplierRepository, PurchaseOrderRepository, StockMovementRepository,
)


class WarehouseService:
    def __init__(self):
        self.repo = WarehouseRepository()

    def list(self): return self.repo.get_all()
    def get(self, pk):
        w = self.repo.get_by_id(pk)
        if not w: raise ValueError(f"Warehouse {pk} not found")
        return w
    def create(self, data): return self.repo.create(**data)
    def update(self, pk, data): return self.repo.update(self.get(pk), **data)
    def delete(self, pk): self.repo.delete(self.get(pk))
    def add_location(self, warehouse_id, data):
        warehouse = self.get(warehouse_id)
        return self.repo.add_location(warehouse, **data)


class InventoryService:
    def __init__(self):
        self.repo = InventoryRepository()
        self.movement_repo = StockMovementRepository()

    def list(self): return self.repo.get_all()
    def get(self, pk):
        inv = self.repo.get_by_id(pk)
        if not inv: raise ValueError(f"Inventory {pk} not found")
        return inv
    def create(self, data): return self.repo.create(**data)
    def adjust_stock(self, inventory_id: int, delta: int, admin_id: int = None, notes: str = ""):
        inv = self.get(inventory_id)
        updated = self.repo.update_stock(inv, delta)
        movement = self.movement_repo.create(
            book_id=inv.book_id,
            to_warehouse=inv.warehouse if delta > 0 else None,
            from_warehouse=inv.warehouse if delta < 0 else None,
            quantity=abs(delta), admin_id=admin_id, notes=notes,
        )
        self.movement_repo.add_log(movement, "adjust", f"Delta: {delta}")
        return updated


class SupplierService:
    def __init__(self): self.repo = SupplierRepository()
    def list(self): return self.repo.get_all()
    def get(self, pk):
        s = self.repo.get_by_id(pk)
        if not s: raise ValueError(f"Supplier {pk} not found")
        return s
    def create(self, data): return self.repo.create(**data)
    def update(self, pk, data): return self.repo.update(self.get(pk), **data)
    def delete(self, pk): self.repo.delete(self.get(pk))


class PurchaseOrderService:
    def __init__(self):
        self.repo = PurchaseOrderRepository()
        self.supplier_repo = SupplierRepository()

    def list(self): return self.repo.get_all()
    def get(self, pk):
        po = self.repo.get_by_id(pk)
        if not po: raise ValueError(f"PurchaseOrder {pk} not found")
        return po
    def create(self, data: dict):
        supplier_id = data.pop("supplier_id")
        items = data.pop("items", [])
        supplier = self.supplier_repo.get_by_id(supplier_id)
        if not supplier: raise ValueError(f"Supplier {supplier_id} not found")
        po = self.repo.create(supplier, **data)
        total = 0
        for item in items:
            self.repo.add_item(po, **item)
            total += item.get("unit_price", 0) * item.get("quantity", 0)
        po.total_amount = total
        po.save(update_fields=["total_amount"])
        return self.repo.get_by_id(po.id)
    def update_status(self, pk, new_status): return self.repo.update_status(self.get(pk), new_status)
