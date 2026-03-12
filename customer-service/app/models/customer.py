from django.db import models
from .user import User


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="customer_profile")
    loyalty_points = models.IntegerField(default=0)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "customers"
        ordering = ["-created_date"]

    def __str__(self):
        return f"Customer({self.user.username})"
