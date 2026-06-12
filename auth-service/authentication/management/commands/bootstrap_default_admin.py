from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or refresh the default admin account (delegates to bootstrap_default_users)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Do not prompt for input.',
        )

    def handle(self, *args, **options):
        call_command("bootstrap_default_users", no_input=options.get("no_input"))