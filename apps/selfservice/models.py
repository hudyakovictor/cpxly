import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Компания", max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Membership(models.Model):
    ROLES = [("owner", "Владелец"), ("member", "Пользователь"), ("viewer", "Просмотр")]
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=12, choices=ROLES, default="viewer")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["company", "user"], name="unique_company_member")]


class ServiceRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    code = models.CharField(max_length=16, default="S-03")
    idempotency_key = models.UUIDField()
    facts = models.JSONField(default=dict)
    use_ai = models.BooleanField(default=False)
    state = models.CharField(max_length=16, default="queued", choices=[
        ("queued", "В очереди"), ("processing", "Обработка"), ("ready", "Черновик готов"), ("failed", "Ошибка"),
        ("needs_review", "Обработка прервана"),
    ])
    attempt_token = models.UUIDField(null=True, editable=False)
    processing_started_at = models.DateTimeField(null=True, editable=False)
    processing_attempts = models.PositiveIntegerField(default=0, editable=False)
    draft = models.TextField(blank=True)
    ai_suggestion = models.TextField(blank=True)
    result_file = models.FileField(upload_to="selfservice", blank=True)
    engine_version = models.CharField(max_length=40, blank=True)
    error = models.CharField(max_length=250, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["company", "idempotency_key"], name="unique_service_submission")]
        ordering = ["-created_at"]


class RequestEvent(models.Model):
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name="events")
    kind = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)


class DispatchRecord(models.Model):
    """Transactional outbox: records intent, never customer text or provider keys."""
    request = models.OneToOneField(ServiceRequest, on_delete=models.CASCADE, primary_key=True, related_name="dispatch_record")
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    publish_attempts = models.PositiveIntegerField(default=0)
    last_published_at = models.DateTimeField(null=True)
    last_error_code = models.CharField(max_length=32, blank=True)
