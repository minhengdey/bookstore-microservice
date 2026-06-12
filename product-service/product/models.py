from django.db import models
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = "categories"
        
    def __str__(self):
        return self.name

class Brand(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = "brands"
        
    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="VND")
    sku = models.CharField(max_length=50, unique=True, null=True, blank=True)
    image_url = models.CharField(max_length=1000, blank=True, default="")
    attributes = models.JSONField(default=dict)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, default="active")
    stock = models.IntegerField(default=0)
    is_flash_sale = models.BooleanField(default=False)
    flash_sale_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    flash_sale_name = models.CharField(max_length=255, blank=True, default="")
    flash_sale_ends_at = models.DateTimeField(null=True, blank=True)
    flash_sale_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"

    def __str__(self):
        return self.name

    def refresh_flash_sale_state(self, save=True):
        if not self.is_flash_sale:
            return False
        if self.flash_sale_ends_at and self.flash_sale_ends_at <= timezone.now():
            self.is_flash_sale = False
            self.flash_sale_price = None
            self.flash_sale_name = ""
            self.flash_sale_ends_at = None
            self.flash_sale_id = None
            if save:
                self.save(update_fields=[
                    "is_flash_sale", "flash_sale_price", "flash_sale_name",
                    "flash_sale_ends_at", "flash_sale_id", "updated_at",
                ])
            return True
        return False

    @property
    def effective_price(self):
        self.refresh_flash_sale_state(save=True)
        if self.is_flash_sale and self.flash_sale_price is not None:
            return self.flash_sale_price
        return self.price

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    color = models.CharField(max_length=50, blank=True, null=True)
    size = models.CharField(max_length=50, blank=True, null=True)
    price_modifier = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock = models.IntegerField(default=0)
    sku = models.CharField(max_length=50, unique=True, null=True, blank=True)

    class Meta:
        db_table = "product_variants"

    def __str__(self):
        return f"{self.product.name} - {self.color} - {self.size}"

class StockReservationLog(models.Model):
    order_id = models.IntegerField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    status = models.CharField(max_length=20, default="RESERVED") # RESERVED, RELEASED, COMMITTED
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "stock_reservation_logs"

class InventoryTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('IMPORT', 'Nhập kho'),
        ('EXPORT', 'Xuất kho'),
        ('ORDER', 'Đơn hàng'),
        ('RETURN', 'Hoàn trả'),
        ('ADJUST', 'Điều chỉnh')
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity_changed = models.IntegerField()
    stock_after = models.IntegerField()
    reference_id = models.CharField(max_length=100, blank=True, null=True, help_text="Order ID, PO ID, etc.")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "inventory_transactions"
        ordering = ['-created_at']
