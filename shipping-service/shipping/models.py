from django.db import models

class ShippingZone(models.Model):
    city_name = models.CharField(max_length=100, unique=True)
    distance_km = models.FloatField(default=15.0)

    class Meta:
        db_table = "shipping_zones"

    def __str__(self):
        return f"{self.city_name} ({self.distance_km} km)"


class ShippingMethod(models.Model):
    method_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    estimated_days = models.PositiveSmallIntegerField(default=5)
    min_weight = models.FloatField(default=0)
    max_weight = models.FloatField(default=0)
    min_distance = models.FloatField(default=0)
    max_distance = models.FloatField(default=0)
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = "shipping_methods"

    def __str__(self):
        return self.method_name

class ShippingFeature(models.Model):
    shipping_method = models.ForeignKey(ShippingMethod, on_delete=models.CASCADE, related_name="features")
    feature = models.CharField(max_length=100)
    value = models.CharField(max_length=255)

    class Meta:
        db_table = "shipping_features"

class ShippingState(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    SHIPPED = "shipped", "Shipped"
    FAILED = "failed", "Failed"

class Shipping(models.Model):
    order_id = models.IntegerField(unique=True)
    tracking_number = models.CharField(max_length=32, unique=True, blank=True)
    shipping_method = models.ForeignKey(ShippingMethod, null=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=50, choices=ShippingState.choices, default=ShippingState.PENDING)
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
