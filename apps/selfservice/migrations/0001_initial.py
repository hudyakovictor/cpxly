import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="Company", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("name", models.CharField(max_length=200, verbose_name="Компания")),
            ("created_at", models.DateTimeField(auto_now_add=True)),
        ]),
        migrations.CreateModel(name="Membership", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("role", models.CharField(choices=[("owner", "Владелец"), ("member", "Пользователь"), ("viewer", "Просмотр")], default="viewer", max_length=12)),
            ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="selfservice.company")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
        ], options={"constraints": [models.UniqueConstraint(fields=("company", "user"), name="unique_company_member")]}),
        migrations.CreateModel(name="ServiceRequest", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("code", models.CharField(default="S-03", max_length=16)),
            ("idempotency_key", models.UUIDField()), ("facts", models.JSONField(default=dict)),
            ("use_ai", models.BooleanField(default=False)),
            ("state", models.CharField(choices=[("queued", "В очереди"), ("processing", "Обработка"), ("ready", "Черновик готов"), ("failed", "Ошибка")], default="queued", max_length=16)),
            ("draft", models.TextField(blank=True)), ("ai_suggestion", models.TextField(blank=True)),
            ("result_file", models.FileField(blank=True, upload_to="selfservice")),
            ("engine_version", models.CharField(blank=True, max_length=40)),
            ("error", models.CharField(blank=True, max_length=250)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="selfservice.company")),
        ], options={"ordering": ["-created_at"], "constraints": [models.UniqueConstraint(fields=("company", "idempotency_key"), name="unique_service_submission")]}),
        migrations.CreateModel(name="RequestEvent", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("kind", models.CharField(max_length=32)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="selfservice.servicerequest")),
        ]),
    ]
