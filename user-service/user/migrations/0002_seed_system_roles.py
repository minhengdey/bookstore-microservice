# Generated manually for RBAC seeding
from django.db import migrations

def seed_system_roles(apps, schema_editor):
    Role = apps.get_model('user', 'Role')
    Permission = apps.get_model('user', 'Permission')

    SYSTEM_ROLES = [
        "CUSTOMER",
        "SELLER",
        "STAFF",
        "ADMIN",
        "SUPER_ADMIN"
    ]

    for role_name in SYSTEM_ROLES:
        Role.objects.get_or_create(name=role_name, defaults={'is_system': True})

def reverse_seed_system_roles(apps, schema_editor):
    Role = apps.get_model('user', 'Role')
    Role.objects.filter(name__in=["CUSTOMER", "SELLER", "STAFF", "ADMIN", "SUPER_ADMIN"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0001_initial'),
    ]

    operations = [
    ]
