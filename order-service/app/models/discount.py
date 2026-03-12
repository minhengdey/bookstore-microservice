from django.db import models


class Discount(models.Model):
    discount_code = models.CharField(max_length=50, unique=True)
    discount_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    is_percentage = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "discounts"

    def __str__(self):
        return f"{self.discount_code} ({self.discount_value}{'%' if self.is_percentage else ''})"
