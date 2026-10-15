# Immutable F1 snapshot: new catalog editions need a NEW snapshot/migration.
import hashlib
import json
from pathlib import Path
from django.db import migrations

SNAPSHOT_SHA256 = '8a0f8c0c6077486798154ce86b0ab00e3d7d5cc6dec40fc0fe73f1063de881ca'


def seed(apps, schema_editor):
    data = (Path(__file__).resolve().parents[1] / "data" / "catalog_v1.json").read_bytes()
    if hashlib.sha256(data).hexdigest() != SNAPSHOT_SHA256:
        raise RuntimeError("Catalog v1 snapshot changed; do not rewrite a historical migration")
    entries = json.loads(data)
    if len(entries) != 57 or {item["code"] for item in entries} != {f"S-{n:02d}" for n in range(1, 58)}:
        raise RuntimeError("Catalog v1 IDs are incomplete or duplicated")
    model = apps.get_model("service_catalog", "ServiceCatalogEntry")
    for record in entries:
        defaults = {k: v for k, v in record.items() if k != "code"}
        defaults.update(stage="placeholder", is_visible_to_clients=False, accepts_requests=False)
        model.objects.using(schema_editor.connection.alias).get_or_create(code=record["code"], defaults=defaults)


class Migration(migrations.Migration):
    dependencies = [("service_catalog", "0001_initial")]
    operations = [migrations.RunPython(seed, reverse_code=migrations.RunPython.noop)]
