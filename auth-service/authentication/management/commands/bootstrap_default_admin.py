import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from authentication.models import AuthUser


class Command(BaseCommand):
    help = "Create or refresh the default admin account."

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Do not prompt for input.',
        )

    def handle(self, *args, **options):
        username = os.environ.get("DEFAULT_ADMIN_USERNAME", "admin").strip()
        email = os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@ecommerce.local").strip().lower()
        password = os.environ.get("DEFAULT_ADMIN_PASSWORD", "Admin@12345")

        if not username:
            raise CommandError("DEFAULT_ADMIN_USERNAME cannot be empty")
        if not email:
            raise CommandError("DEFAULT_ADMIN_EMAIL cannot be empty")

        existing_email_user = AuthUser.objects.filter(email=email).exclude(username=username).first()
        if existing_email_user:
            raise CommandError(
                f"Default admin email {email} is already used by another account ({existing_email_user.username})"
            )

        with transaction.atomic():
            user = AuthUser.objects.filter(username=username).first()
            created = user is None

            if created:
                user = AuthUser.objects.create_superuser(username=username, email=email, password=password)
            else:
                user.email = email
                user.is_staff = True
                user.is_superuser = True
                user.is_active = True
                user.set_password(password)
                user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created default admin account: {username}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Refreshed default admin account: {username}"))