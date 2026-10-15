import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


def backfill_queued(apps, schema_editor):
    Request = apps.get_model("selfservice", "ServiceRequest")
    Outbox = apps.get_model("selfservice", "DispatchRecord")
    alias = schema_editor.connection.alias
    pending = []
    for pk in Request.objects.using(alias).filter(state="queued").values_list("pk", flat=True).iterator(chunk_size=500):
        pending.append(Outbox(request_id=pk))
        if len(pending) >= 500:
            Outbox.objects.using(alias).bulk_create(pending, ignore_conflicts=True)
            pending = []
    if pending:
        Outbox.objects.using(alias).bulk_create(pending, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [("selfservice", "0001_initial")]
    operations = [
        migrations.AddField(model_name="servicerequest", name="attempt_token", field=models.UUIDField(editable=False, null=True)),
        migrations.AddField(model_name="servicerequest", name="processing_started_at", field=models.DateTimeField(editable=False, null=True)),
        migrations.AddField(model_name="servicerequest", name="processing_attempts", field=models.PositiveIntegerField(default=0, editable=False)),
        migrations.AlterField(model_name="servicerequest", name="state", field=models.CharField(choices=[("queued", "В очереди"), ("processing", "Обработка"), ("ready", "Черновик готов"), ("failed", "Ошибка"), ("needs_review", "Обработка прервана")], default="queued", max_length=16)),
        migrations.CreateModel(name="DispatchRecord", fields=[
            ("request", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name="dispatch_record", serialize=False, to="selfservice.servicerequest")),
            ("next_attempt_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
            ("publish_attempts", models.PositiveIntegerField(default=0)),
            ("last_published_at", models.DateTimeField(null=True)),
            ("last_error_code", models.CharField(blank=True, max_length=32)),
        ]),
        migrations.RunPython(backfill_queued, reverse_code=migrations.RunPython.noop),
    ]
