from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from apps.service_catalog.models import ServiceCatalogEntry

class Command(BaseCommand):
    help="Explicitly activate synthetic S-03; not a production readiness declaration."
    def add_arguments(self, parser):
        parser.add_argument("--confirm-synthetic-only", action="store_true")
    def handle(self, *args, **options):
        if not options["confirm_synthetic_only"] or not settings.CAPEXLY_SANDBOX_MODE or not settings.CAPEXLY_PILOT_ENABLED:
            raise CommandError("Set synthetic pilot flag and confirm; no activation performed")
        item=ServiceCatalogEntry.objects.get(code="S-03")
        item.stage="development"; item.is_visible_to_clients=True; item.accepts_requests=True
        item.full_clean(); item.save(update_fields=["stage","is_visible_to_clients","accepts_requests"])
        self.stdout.write("Activated S-03 for synthetic pilot only. Other entries unchanged.")
