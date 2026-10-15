"""At-least-once dispatch; DB guards, not an exactly-once provider guarantee."""
import logging
import uuid
from datetime import timedelta
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone
from .ai import optional_rewrite
from .claim_engine import VERSION, build_draft, to_docx
from .models import Company, DispatchRecord, Membership, RequestEvent, ServiceRequest
from .reliability import STALE_AFTER_SECONDS, MAX_TEMPLATE_ATTEMPTS, dispatch_delay, owns_attempt, require_transition

logger = logging.getLogger(__name__)


def _event(case, kind):
    RequestEvent.objects.create(request=case, kind=kind)


def _discard(filename):
    if filename:
        try:
            default_storage.delete(filename)  # Only this attempt's unpublished object.
        except Exception as exc:
            logger.warning("Unpublished output cleanup failed: %s", type(exc).__name__)


def _authorized(case):
    return Membership.objects.filter(company_id=case.company_id, user_id=case.actor_id, role__in=["owner", "member"]).exists()


@shared_task(acks_late=True, reject_on_worker_lost=True)
def build_claim(request_id):
    # Same Company -> Request lock order as access changes; never trust broker args as permission.
    company_id = ServiceRequest.objects.filter(pk=request_id).values_list("company_id", flat=True).first()
    if company_id is None:
        return
    with transaction.atomic():
        Company.objects.select_for_update().get(pk=company_id)
        case = ServiceRequest.objects.select_for_update().get(pk=request_id)
        if case.state != "queued":
            return
        if not _authorized(case) or case.processing_attempts >= MAX_TEMPLATE_ATTEMPTS:
            require_transition(case.state, "failed")
            case.state, case.error = "failed", "Доступ отозван или лимит обработок исчерпан"
            case.save(update_fields=["state", "error"])
            _event(case, "start_refused")
            return
        require_transition(case.state, "processing")
        token = uuid.uuid4()
        case.state, case.attempt_token = "processing", token
        case.processing_started_at = timezone.now()
        case.processing_attempts += 1
        case.error = ""
        case.save(update_fields=["state", "attempt_token", "processing_started_at", "processing_attempts", "error"])
        _event(case, "processing")
    filename = None
    try:
        draft = build_draft(case.facts)
        suggestion = ""
        if case.use_ai:
            suggestion = optional_rewrite(case.facts, enabled=settings.CAPEXLY_EXTERNAL_AI_ENABLED,
                provider=settings.CAPEXLY_AI_PROVIDER, model=settings.CAPEXLY_AI_MODEL,
                key_file=settings.CAPEXLY_AI_KEY_FILE)
        # Generation token gives each attempt a distinct private object prefix.
        filename = default_storage.save(f"selfservice/{case.company_id}/{case.id}/{token}/{VERSION}.docx", ContentFile(to_docx(draft)))
        with transaction.atomic():
            Company.objects.select_for_update().get(pk=company_id)
            current = ServiceRequest.objects.select_for_update().get(pk=case.pk)
            if not owns_attempt(current.state, current.attempt_token, token):
                # Reaper/recovery may have fenced this attempt. It cannot publish late.
                _discard(filename)
                return
            if not _authorized(current):
                raise PermissionError("Membership revoked")
            require_transition(current.state, "ready")
            current.draft, current.ai_suggestion = draft, suggestion
            current.result_file.name = filename
            current.engine_version, current.state, current.error = VERSION, "ready", ""
            current.save(update_fields=["draft", "ai_suggestion", "result_file", "engine_version", "state", "error"])
            _event(current, "draft_ready")
    except Exception as exc:
        # A publish commit can be ambiguous if the DB connection dies during commit.
        # Never delete a file that could already be a committed published result.
        if filename:
            try:
                published = ServiceRequest.objects.filter(pk=case.pk, result_file=filename).exists()
            except Exception:
                published = True  # Fail safe: retain possible orphan for explicit review.
            if not published:
                _discard(filename)
        with transaction.atomic():
            current = ServiceRequest.objects.select_for_update().get(pk=case.pk)
            if owns_attempt(current.state, current.attempt_token, token):
                require_transition(current.state, "failed")
                current.state = "failed"
                current.error = "Не удалось завершить обработку. Автоматического повторного ИИ-вызова нет."
                current.save(update_fields=["state", "error"])
                _event(current, "attempt_failed")
        logger.warning("Synthetic pilot failed: %s", type(exc).__name__)


def dispatch_one(request_id):
    """Persist-before-publish. Broker failure leaves queued intent in PostgreSQL."""
    now = timezone.now()
    with transaction.atomic():
        case = ServiceRequest.objects.select_for_update(skip_locked=True).filter(pk=request_id).first()
        if case is None or case.state != "queued":
            return False
        record = DispatchRecord.objects.select_for_update().filter(request=case).first()
        if record is None or record.next_attempt_at > now:
            return False
        record.publish_attempts += 1
        try:
            # No publisher retries inside a DB transaction. Duplicates after ambiguous
            # acceptance are safe at request claim, not an exactly-once network claim.
            build_claim.apply_async(args=[str(case.pk)], retry=False)
        except Exception as exc:
            record.last_error_code = "broker_unavailable"
            record.next_attempt_at = now + timedelta(seconds=dispatch_delay(record.publish_attempts))
            logger.warning("Outbox publish unavailable: %s", type(exc).__name__)
        else:
            record.last_published_at = now
            record.last_error_code = ""
            # Republish only if still queued after a grace interval (e.g. lost Redis message).
            record.next_attempt_at = now + timedelta(seconds=60)
        record.save(update_fields=["publish_attempts", "last_published_at", "last_error_code", "next_attempt_at"])
        return not record.last_error_code


def enqueue_case(case_id):
    """Best effort low-latency wake-up; periodic outbox scan is the durable path."""
    try:
        dispatch_one(case_id)
    except Exception as exc:
        # Intent was already committed by the request view; do not mark the request failed.
        logger.warning("Outbox wake-up deferred: %s", type(exc).__name__)


@shared_task(ignore_result=True)
def dispatch_pending():
    ids = list(DispatchRecord.objects.filter(request__state="queued", next_attempt_at__lte=timezone.now())
               .order_by("next_attempt_at").values_list("request_id", flat=True)[:50])
    for request_id in ids:
        enqueue_case(request_id)


@shared_task(ignore_result=True)
def mark_stale_processing():
    cutoff = timezone.now() - timedelta(seconds=STALE_AFTER_SECONDS)
    # Legacy processing rows have no timestamp: flag for review too, never auto-replay.
    from django.db.models import Q
    ids = list(ServiceRequest.objects.filter(state="processing")
               .filter(Q(processing_started_at__lt=cutoff) | Q(processing_started_at__isnull=True))
               .order_by("created_at").values_list("pk", flat=True)[:50])
    for pk in ids:
        with transaction.atomic():
            current = ServiceRequest.objects.select_for_update(skip_locked=True).filter(pk=pk).first()
            if current is None or current.state != "processing":
                continue
            if current.processing_started_at and current.processing_started_at >= cutoff:
                continue
            require_transition(current.state, "needs_review")
            current.state = "needs_review"
            current.error = "Обработка прервана или превысила лимит ожидания. Повтор автоматически не выполняется."
            current.save(update_fields=["state", "error"])
            _event(current, "stale_requires_review")
