from django.db import models
from .user import User


class InventoryStaff(models.Model):
    ROLE_STAFF   = "staff"
    ROLE_MANAGER = "manager"
    ROLE_CHOICES = [(ROLE_STAFF, "Staff"), (ROLE_MANAGER, "Manager")]

    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name="staff_profile")
    storage_code = models.CharField(max_length=50, unique=True)
    department   = models.CharField(max_length=255, blank=True)
    position     = models.CharField(max_length=255, blank=True)
    role         = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STAFF)

    class Meta:
        db_table = "inventory_staff"
        verbose_name_plural = "inventory staff"

    def __str__(self):
        return f"Staff({self.user.username}, {self.position}, {self.role})"
