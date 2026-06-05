import logging
from django.core.management.base import BaseCommand
from user.models import Role, Permission

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Seeds initial RBAC Roles and Permissions (Idempotent)'

    def handle(self, *args, **options):
        # Define operational permissions
        perms = [
            ("view_users", "Can view users"),
            ("manage_users", "Can manage users"),
            ("view_orders", "Can view orders"),
            ("manage_orders", "Can manage orders"),
            ("manage_inventory", "Can manage inventory"),
            ("manage_catalog", "Can manage product catalog"),
        ]

        created_perms = []
        for code, desc in perms:
            p, created = Permission.objects.get_or_create(code=code, defaults={'description': desc})
            created_perms.append(p)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created permission: {code}'))

        # Define operational extended roles if needed, system roles are handled by migrations
        # But we ensure they exist here too just in case
        SYSTEM_ROLES = ["CUSTOMER", "SELLER", "STAFF", "ADMIN", "SUPER_ADMIN", "SUPPORT"]
        for role_name in SYSTEM_ROLES:
            r, created = Role.objects.get_or_create(name=role_name, defaults={'is_system': True})
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created role: {role_name}'))

        # Map permissions to roles
        role_mappings = {
            "ADMIN": ["view_users", "manage_users", "view_orders", "manage_orders", "manage_inventory", "manage_catalog"],
            "STAFF": ["view_orders", "manage_orders", "manage_inventory", "manage_catalog"],
            "SUPPORT": ["view_users", "view_orders"],
            "SELLER": [], # Seller permissions handled via SellerProfile / specialized checks
            "CUSTOMER": []
        }

        for role_name, perm_codes in role_mappings.items():
            role = Role.objects.filter(name=role_name).first()
            if role:
                perms_to_add = Permission.objects.filter(code__in=perm_codes)
                role.permissions.add(*perms_to_add)
                self.stdout.write(self.style.SUCCESS(f'Mapped {len(perms_to_add)} permissions to role: {role_name}'))

        self.stdout.write(self.style.SUCCESS('RBAC seeding and mapping complete!'))
