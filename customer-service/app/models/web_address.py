from django.db import models
from .customer import Customer


class WebAddress(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="addresses")
    recipient_name = models.CharField(max_length=255)
    address_line = models.CharField(max_length=500)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    phone = models.CharField(max_length=20, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = "web_addresses"

    def __str__(self):
        return f"{self.recipient_name} – {self.city}, {self.country}"
