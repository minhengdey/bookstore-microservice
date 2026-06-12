from django.db import models

class Voucher(models.Model):
    code = models.CharField(max_length=50, unique=True)

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    min_order_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    usage_limit = models.IntegerField(default=1)
    used_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code

class FlashSale(models.Model):
    name = models.CharField(max_length=255)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class FlashSaleItem(models.Model):
    flash_sale = models.ForeignKey(FlashSale, related_name='items', on_delete=models.CASCADE)
    product_id = models.IntegerField()
    discount_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.IntegerField()
    sold_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.flash_sale.name} - Product {self.product_id}"
