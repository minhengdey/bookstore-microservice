from django.db import models
from .shipping_method import ShippingMethod


class Shipping(models.Model):
    order_id = models.IntegerField(unique=True)    # ref → order-service
    shipping_method = models.ForeignKey(ShippingMethod, null=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=50, default="pending")
    estimated_delivery_date = models.DateField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "shippings"


class ShippingAddress(models.Model):
    shipping = models.OneToOneField(Shipping, on_delete=models.CASCADE, related_name="address")
    recipient_name = models.CharField(max_length=255)
    address_line = models.CharField(max_length=500)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    phone = models.CharField(max_length=20, blank=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "shipping_addresses"


class ShippingStatus(models.Model):
    shipping = models.ForeignKey(Shipping, on_delete=models.CASCADE, related_name="statuses")
    status = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    updated_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "shipping_statuses"
        ordering = ["-updated_date"]
