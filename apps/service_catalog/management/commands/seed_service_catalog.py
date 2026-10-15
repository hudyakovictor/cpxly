"""Explicit idempotent metadata bootstrap; never overwrites administrator edits."""
import hashlib
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.service_catalog.models import ServiceCatalogEntry


class Command(BaseCommand):
    help = "Добавить отсутствующие заглушки F1 без перезаписи существующих записей"

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(__file__).resolve().parents[2] / "data" / "catalog_v1.json"
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != '8a0f8c0c6077486798154ce86b0ab00e3d7d5cc6dec40fc0fe73f1063de881ca':
            raise CommandError("Снимок F1 изменён: требуется отдельная версия импорта")
        created = 0
        for item in json.loads(data):
            defaults = {k: v for k, v in item.items() if k != "code"}
            defaults.update(stage="placeholder", is_visible_to_clients=False, accepts_requests=False)
            _, was_created = ServiceCatalogEntry.objects.get_or_create(code=item["code"], defaults=defaults)
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Добавлено: {created}. Существующие записи не изменены."))
