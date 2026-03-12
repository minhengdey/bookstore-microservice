from django.db import models


class CouponStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    USED = "used", "Used"
    EXPIRED = "expired", "Expired"


class Coupon(models.Model):
    customer_id = models.IntegerField()   # ref → customer-service
    order_id = models.IntegerField(null=True, blank=True)
    coupon_code = models.CharField(max_length=50, unique=True)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    is_percentage = models.BooleanField(default=True)
    expiry_date = models.DateField()
    status = models.CharField(max_length=20, choices=CouponStatus.choices, default=CouponStatus.ACTIVE)

    class Meta:
        db_table = "coupons"
