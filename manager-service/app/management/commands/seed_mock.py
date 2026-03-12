"""
Tạo dữ liệu mẫu: Warehouse, WarehouseLocation, Supplier, Inventory, PurchaseOrder, PurchaseOrderItem, StockMovement, StockMovementLog, StockTransfer.
Giả định book-service đã seed (book_id 1-5), staff-service đã seed (admin_id 1).
Chạy: python manage.py seed_mock
"""
from decimal import Decimal
from datetime import date
from django.core.management.base import BaseCommand
from app.models import (
    Warehouse, WarehouseLocation, Supplier, Inventory,
    PurchaseOrder, PurchaseOrderItem, StockMovement, StockMovementLog, StockTransfer,
)
from app.models.purchase_order import POStatus


class Command(BaseCommand):
    help = "Seed mock data: warehouses, suppliers, inventory, purchase orders, stock movements"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Xóa dữ liệu cũ trước khi seed")

    def handle(self, *args, **options):
        if options.get("clear"):
            StockMovementLog.objects.all().delete()
            StockMovement.objects.all().delete()
            StockTransfer.objects.all().delete()
            PurchaseOrderItem.objects.all().delete()
            PurchaseOrder.objects.all().delete()
            Inventory.objects.all().delete()
            WarehouseLocation.objects.all().delete()
            Warehouse.objects.all().delete()
            Supplier.objects.all().delete()
            self.stdout.write(self.style.WARNING("Đã xóa dữ liệu manager."))

        if Warehouse.objects.exists():
            self.stdout.write(self.style.NOTICE("Đã có dữ liệu manager, bỏ qua seed."))
            return

        wh1 = Warehouse.objects.create(
            warehouse_name="Kho TP.HCM",
            warehouse_code="WH-HCM01",
            address="Quận 12, TP.HCM",
            phone="0281234567",
            manager_id=1,
            capacity=10000,
        )
        WarehouseLocation.objects.create(
            warehouse=wh1,
            location_code="A-01-01",
            location_name="Kệ A tầng 1",
            row_number="A",
            column_number="01",
            floor_number="1",
            capacity=500,
        )
        wh2 = Warehouse.objects.create(
            warehouse_name="Kho Hà Nội",
            warehouse_code="WH-HN01",
            address="Đống Đa, Hà Nội",
            phone="0241234567",
            manager_id=1,
            capacity=8000,
        )
        WarehouseLocation.objects.create(
            warehouse=wh2,
            location_code="B-01-01",
            location_name="Kệ B tầng 1",
            capacity=400,
        )

        sup1 = Supplier.objects.create(
            supplier_name="Công ty Sách ABC",
            contact_name="Nguyễn Văn A",
            email="abc@supplier.com",
            phone="0901234567",
            address="TP.HCM",
        )
        Supplier.objects.create(
            supplier_name="NXB Trẻ",
            contact_name="Phòng kinh doanh",
            email="kinhdoanh@nxbtre.com.vn",
            phone="02839316266",
        )

        for book_id in range(1, 6):
            Inventory.objects.create(
                book_id=book_id,
                warehouse=wh1,
                stock_quantity=50 + book_id * 10,
                min_quantity=10,
                max_quantity=200,
            )
            if book_id <= 3:
                Inventory.objects.create(
                    book_id=book_id,
                    warehouse=wh2,
                    stock_quantity=30,
                    min_quantity=5,
                    max_quantity=100,
                )

        po = PurchaseOrder.objects.create(
            supplier=sup1,
            admin_id=1,
            expected_date=date.today(),
            status=POStatus.APPROVED,
            notes="Đơn nhập mẫu",
            total_amount=Decimal("5000000"),
        )
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            book_id=1,
            quantity=100,
            unit_price=Decimal("50000"),
        )
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            book_id=2,
            quantity=80,
            unit_price=Decimal("45000"),
        )

        mov = StockMovement.objects.create(
            book_id=1,
            from_warehouse=None,
            to_warehouse=wh1,
            quantity=100,
            admin_id=1,
            notes="Nhập từ PO",
        )
        StockMovementLog.objects.create(movement=mov, action="RECEIVE", description="Nhập kho từ đơn mua")

        StockTransfer.objects.create(
            from_warehouse=wh1,
            to_warehouse=wh2,
            book_id=1,
            quantity=20,
            admin_id=1,
            status="completed",
        )

        self.stdout.write(self.style.SUCCESS(
            "Created warehouses, locations, suppliers, inventory, purchase order, stock movement & transfer."
        ))
