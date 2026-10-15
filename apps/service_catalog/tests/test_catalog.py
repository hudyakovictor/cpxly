from io import StringIO
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from apps.service_catalog.models import ServiceCatalogEntry
from apps.service_catalog.registry import require_handler


class CatalogTests(TestCase):
    def seed(self):
        call_command("seed_service_catalog", stdout=StringIO())

    def test_source_ids_are_complete_and_disabled(self):
        self.seed()
        rows = ServiceCatalogEntry.objects.filter(code__in=[f"S-{n:02d}" for n in range(1, 58)])
        self.assertEqual(rows.count(), 57)
        self.assertFalse(rows.filter(is_visible_to_clients=True).exists())
        self.assertFalse(rows.filter(accepts_requests=True).exists())
        self.assertEqual(set(rows.values_list("stage", flat=True)), {"placeholder"})

    def test_repeat_import_preserves_admin_edits(self):
        self.seed()
        item = ServiceCatalogEntry.objects.get(code="S-03")
        item.name = "Название, отредактированное администратором"
        item.notes = "Сохранить эту заметку"
        item.save()
        self.seed()
        item.refresh_from_db()
        self.assertEqual(item.notes, "Сохранить эту заметку")
        self.assertEqual(item.name, "Название, отредактированное администратором")
        self.assertEqual(ServiceCatalogEntry.objects.filter(code="S-03").count(), 1)

    def test_classes_and_conflicting_source_flags_preserved(self):
        self.seed()
        self.assertEqual(ServiceCatalogEntry.objects.get(code="S-01").kind, "bundle")
        self.assertEqual(ServiceCatalogEntry.objects.get(code="S-36").kind, "platform")
        self.assertEqual(ServiceCatalogEntry.objects.get(code="S-53").kind, "commercial")
        self.assertTrue(ServiceCatalogEntry.objects.get(code="S-09").source_conflict)

    def test_placeholder_cannot_be_published_or_ordered(self):
        self.seed()
        item = ServiceCatalogEntry.objects.get(code="S-04")
        item.is_visible_to_clients = True
        item.accepts_requests = True
        with self.assertRaises(ValidationError):
            item.full_clean()
        self.assertFalse(item.can_be_requested)
        with self.assertRaises(NotImplementedError):
            require_handler(item.code)
