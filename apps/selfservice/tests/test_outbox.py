"""Prepared PostgreSQL integration tests; NOT run in the agent sandbox.
Uses mocks for broker/S3 fault injection, never as proof of Redis/Garage operation.
"""
import uuid
from datetime import timedelta
from io import StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone
from apps.selfservice.models import Company, DispatchRecord, Membership, RequestEvent, ServiceRequest
from apps.selfservice.tasks import build_claim, dispatch_one, mark_stale_processing
from .test_engine import sample


@override_settings(CELERY_TASK_ALWAYS_EAGER=False, CAPEXLY_SANDBOX_MODE=True, CAPEXLY_EXTERNAL_AI_ENABLED=False)
class OutboxIntegrationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="outbox", email="outbox@example.test", password="synthetic-only")
        self.company = Company.objects.create(name="Synthetic outbox")
        self.member = Membership.objects.create(company=self.company, user=self.user, role="owner")
        self.case = ServiceRequest.objects.create(company=self.company, actor=self.user, facts=sample(), idempotency_key=uuid.uuid4())
        self.record = DispatchRecord.objects.create(request=self.case)

    @patch("apps.selfservice.tasks.build_claim.apply_async", side_effect=ConnectionError("synthetic fault"))
    def test_broker_failure_keeps_queued_intent(self, send):
        self.assertFalse(dispatch_one(self.case.pk))
        self.case.refresh_from_db(); self.record.refresh_from_db()
        self.assertEqual(self.case.state, "queued")
        self.assertEqual(self.record.publish_attempts, 1)
        self.assertEqual(self.record.last_error_code, "broker_unavailable")
        self.assertGreater(self.record.next_attempt_at, timezone.now())

    @patch("apps.selfservice.tasks.build_claim.apply_async")
    def test_publish_does_not_mean_ready(self, send):
        self.assertTrue(dispatch_one(self.case.pk))
        self.case.refresh_from_db(); self.record.refresh_from_db()
        self.assertEqual(self.case.state, "queued")
        self.assertIsNotNone(self.record.last_published_at)
        send.assert_called_once()
        self.assertFalse(dispatch_one(self.case.pk))  # Grace interval, not a second immediate send.

    @patch("apps.selfservice.tasks.build_claim.apply_async")
    def test_ready_not_redispatched(self, send):
        self.case.state = "ready"; self.case.save()
        self.assertFalse(dispatch_one(self.case.pk))
        send.assert_not_called()

    @patch("apps.selfservice.tasks.optional_rewrite")
    @patch("apps.selfservice.tasks.default_storage")
    def test_duplicate_delivery_no_second_work(self, storage, rewrite):
        self.case.state = "processing"; self.case.attempt_token = uuid.uuid4(); self.case.save()
        build_claim(str(self.case.pk))
        storage.save.assert_not_called(); rewrite.assert_not_called()

    @patch("apps.selfservice.tasks.default_storage")
    def test_revoked_actor_not_processed(self, storage):
        self.member.delete()
        build_claim(str(self.case.pk))
        self.case.refresh_from_db()
        self.assertEqual(self.case.state, "failed")
        storage.save.assert_not_called()

    def test_stale_moves_to_review_without_requeue(self):
        self.case.state = "processing"; self.case.use_ai = True
        self.case.attempt_token = uuid.uuid4()
        self.case.processing_started_at = timezone.now() - timedelta(minutes=16)
        self.case.save()
        with patch("apps.selfservice.tasks.build_claim.apply_async") as send:
            mark_stale_processing()
            send.assert_not_called()
        self.case.refresh_from_db()
        self.assertEqual(self.case.state, "needs_review")
        self.assertTrue(RequestEvent.objects.filter(request=self.case, kind="stale_requires_review").exists())

    def test_legacy_processing_marked_for_review(self):
        self.case.state = "processing"; self.case.save()
        mark_stale_processing(); self.case.refresh_from_db()
        self.assertEqual(self.case.state, "needs_review")

    def test_recent_processing_not_expired(self):
        self.case.state = "processing"; self.case.processing_started_at = timezone.now(); self.case.save()
        mark_stale_processing(); self.case.refresh_from_db()
        self.assertEqual(self.case.state, "processing")

    @patch("apps.selfservice.tasks.default_storage")
    def test_fenced_attempt_cannot_publish_late(self, storage):
        def interrupt(*args, **kwargs):
            ServiceRequest.objects.filter(pk=self.case.pk).update(state="needs_review")
            return "synthetic/unpublished.docx"
        storage.save.side_effect = interrupt
        build_claim(str(self.case.pk)); self.case.refresh_from_db()
        self.assertEqual(self.case.state, "needs_review")
        self.assertFalse(self.case.result_file)
        storage.delete.assert_called_once_with("synthetic/unpublished.docx")

    def test_recovery_inspection_is_read_only(self):
        self.case.state = "needs_review"; self.case.save()
        before = RequestEvent.objects.filter(request=self.case).count()
        call_command("recover_service_request", str(self.case.pk), stdout=StringIO())
        self.case.refresh_from_db()
        self.assertEqual(self.case.state, "needs_review")
        self.assertEqual(before, RequestEvent.objects.filter(request=self.case).count())

    def test_ai_recovery_refused_even_with_flags(self):
        self.case.state = "needs_review"; self.case.use_ai = True; self.case.save()
        with self.assertRaises(CommandError):
            call_command("recover_service_request", str(self.case.pk), apply=True, confirm_template_only=True, stdout=StringIO())
        self.case.refresh_from_db(); self.assertEqual(self.case.state, "needs_review")

    def test_template_recovery_retires_old_generation(self):
        self.case.state = "needs_review"; self.case.attempt_token = uuid.uuid4(); self.case.processing_attempts = 1; self.case.save()
        with patch("apps.selfservice.management.commands.recover_service_request.enqueue_case") as wake:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("recover_service_request", str(self.case.pk), apply=True, confirm_template_only=True, stdout=StringIO())
            wake.assert_called_once()
        self.case.refresh_from_db()
        self.assertEqual(self.case.state, "queued"); self.assertIsNone(self.case.attempt_token)
        self.assertTrue(RequestEvent.objects.filter(request=self.case, kind="manual_template_requeue").exists())

    def test_ready_request_cannot_be_reset(self):
        self.case.state = "ready"; self.case.save()
        with self.assertRaises(CommandError):
            call_command("recover_service_request", str(self.case.pk), apply=True, confirm_template_only=True, stdout=StringIO())
