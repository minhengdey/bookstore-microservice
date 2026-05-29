from django.core.management.base import BaseCommand
from app.models import BehaviorEvent
from django.utils.dateparse import parse_datetime
from datetime import datetime

class Command(BaseCommand):
    help = 'Seed specific behavioral data from the user request'

    def handle(self, *args, **options):
        # Data mapping: (user_id_str, product_id_str, action, session, device, persona, timestamp_str)
        # Note: product_name and category are implicitly linked to product_id in our system, 
        # but for the behavior log we only store IDs.
        data = [
            ("U143", "P022", "search", None, None, None, "2024-01-01 03:22:20"),
            ("U143", "P022", "view", "S1766", "desktop", "buyer", "2024-01-01 03:24:28"),
            ("U143", "P022", "click", "S1766", "desktop", "buyer", "2024-01-01 03:24:47"),
            ("U143", "P022", "purchase", "S1766", "desktop", "buyer", "2024-01-01 03:26:19"),
            ("U143", "P084", "search", "S1766", "desktop", "buyer", "2024-01-01 03:28:11"),
            ("U143", "P084", "view", "S1766", "desktop", "buyer", "2024-01-01 03:30:08"),
            ("U143", "P084", "view", "S1766", "desktop", "buyer", "2024-01-01 03:30:32"),
            ("U143", "P084", "search", "S1766", "desktop", "buyer", "2024-01-01 03:32:33"),
            ("U467", "P046", "search", "S4653", "mobile", "buyer", "2024-01-01 04:33:15"),
            ("U467", "P078", "view", "S4653", "mobile", "buyer", "2024-01-01 04:34:21"),
            ("U467", "P078", "add_to_cart", "S4653", "mobile", "buyer", "2024-01-01 04:36:03"),
            ("U467", "P078", "purchase", "S4653", "mobile", "buyer", "2024-01-01 04:37:03"),
            ("U467", "P078", "view", "S4653", "mobile", "buyer", "2024-01-01 04:39:45"),
            ("U467", "P078", "view", "S4653", "mobile", "buyer", "2024-01-01 04:39:57"),
            ("U467", "P078", "click", "S4653", "mobile", "buyer", "2024-01-01 04:41:30"),
            ("U467", "P094", "view", "S4653", "mobile", "buyer", "2024-01-01 04:43:25"),
            ("U467", "P094", "add_to_cart", "S4653", "mobile", "buyer", "2024-01-01 04:44:50"),
            ("U467", "P094", "add_to_cart", "S4653", "mobile", "buyer", "2024-01-01 04:45:35"),
            ("U467", "P094", "purchase", "S4653", "mobile", "buyer", "2024-01-01 04:45:45"),
            ("U038", "P094", "search", "S3523", "desktop", "browser", "2024-01-01 05:42:04"),
        ]

        # Action weights mapping
        weights = {
            "search": 0.5,
            "view": 1.0,
            "click": 1.5,
            "add_to_cart": 3.0,
            "purchase": 5.0
        }

        created_count = 0
        for u_id_str, p_id_str, action, session, device, persona, ts_str in data:
            # Strip prefixes 'U' and 'P' to get integer IDs
            customer_id = int(u_id_str[1:])
            product_id = int(p_id_str[1:])
            
            event_time = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            
            BehaviorEvent.objects.create(
                customer_id=customer_id,
                product_id=product_id,
                action=action,
                action_weight=weights.get(action, 1.0),
                session_id=session,
                device=device,
                persona=persona,
                event_time=event_time
            )
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {created_count} behavioral events!"))
