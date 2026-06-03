import uuid
from django.db import models
from django.utils import timezone

class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        self.deleted_at = None
        self.save()

class UserRole(models.TextChoices):
    CUSTOMER = "customer", "Customer"
    STAFF = "staff", "Staff"
    MANAGER = "manager", "Manager"
    ADMIN = "admin", "Admin"

class UserProfile(SoftDeleteModel):
    auth_user_id = models.UUIDField(primary_key=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.CUSTOMER)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True)
    avatar_url = models.URLField(blank=True)
    gender = models.CharField(max_length=10, blank=True)
    birthday = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_profiles"

    def __str__(self):
        return f"UserProfile({self.auth_user_id})"

class CustomerProfile(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name="customer_profile")
    loyalty_points = models.IntegerField(default=0)

    class Meta:
        db_table = "customer_profiles"

    def __str__(self):
        return f"CustomerProfile({self.user_profile.auth_user_id})"

class StaffProfile(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name="staff_profile")
    storage_code = models.CharField(max_length=50, blank=True)
    department = models.CharField(max_length=255, blank=True)
    position = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "staff_profiles"

    def __str__(self):
        return f"StaffProfile({self.user_profile.auth_user_id}, {self.position})"

class WebAddress(models.Model):
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name="addresses")
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
