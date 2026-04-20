from django.db import models

class ProductModel(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey('CategoryModel', on_delete=models.CASCADE, related_name='products')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='VND')
    sku = models.CharField(max_length=50, unique=True, null=True, blank=True)
    attributes = models.JSONField(default=dict) # JSONB in Postgres
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return self.name

class CategoryModel(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'categories'
        
    def __str__(self):
        return self.name
