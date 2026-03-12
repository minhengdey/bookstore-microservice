from django.db import models


class ShippingMethod(models.Model):
    method_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
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
