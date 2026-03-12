from django.db import models


class Supplier(models.Model):
    supplier_name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    fax = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = "suppliers"

    def __str__(self):
        return self.supplier_name
