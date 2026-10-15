import uuid
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from apps.selfservice.models import DispatchRecord, RequestEvent, ServiceRequest
from apps.selfservice.reliability import recovery_error, require_transition
from apps.selfservice.tasks import enqueue_case


class Command(BaseCommand):
    help = "Inspect by default; explicit recovery only for a synthetic, non-AI failed request."

    def add_arguments(self, parser):
        parser.add_argument("request_id", type=uuid.UUID)
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--confirm-template-only", action="store_true")

    def handle(self, *args, **options):
        if not settings.CAPEXLY_SANDBOX_MODE:
            raise CommandError("Recovery only supported in the synthetic pilot")
        with transaction.atomic():
            try:
                case = ServiceRequest.objects.select_for_update().get(pk=options["request_id"])
            except ServiceRequest.DoesNotExist:
                raise CommandError("Request not found") from None
            # Print only technical state, never facts or credentials.
            self.stdout.write(f"state={case.state}; attempts={case.processing_attempts}; ai={case.use_ai}; file={bool(case.result_file)}")
            if not options["apply"]:
                self.stdout.write("Inspection only; nothing changed")
                return
            error = recovery_error(state=case.state, use_ai=case.use_ai, has_file=bool(case.result_file),
                                   confirmed=options["confirm_template_only"], attempts=case.processing_attempts)
            if error:
                raise CommandError(error)
            require_transition(case.state, "queued")
            case.state, case.error = "queued", ""
            # Retire the old generation; any old worker completion must fail its token check.
            case.attempt_token = None
            case.processing_started_at = None
            case.save(update_fields=["state", "error", "attempt_token", "processing_started_at"])
            DispatchRecord.objects.update_or_create(request=case, defaults={"next_attempt_at": timezone.now(), "last_error_code": ""})
            RequestEvent.objects.create(request=case, kind="manual_template_requeue")
            transaction.on_commit(lambda: enqueue_case(case.pk))
        self.stdout.write("Template-only request requeued; no rows or files deleted")
