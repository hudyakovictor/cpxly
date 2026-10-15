"""Pure policy tests: no Django, broker, storage, network or installed services."""
import unittest
from uuid import uuid4
from apps.selfservice.reliability import (
    MAX_TEMPLATE_ATTEMPTS, STALE_AFTER_SECONDS, TRANSITIONS,
    dispatch_delay, owns_attempt, recovery_error, require_transition,
)


class ReliabilityPolicyTests(unittest.TestCase):
    def test_transition_matrix(self):
        for before in TRANSITIONS:
            for after in TRANSITIONS:
                with self.subTest(before=before, after=after):
                    if after in TRANSITIONS[before]:
                        require_transition(before, after)
                    else:
                        with self.assertRaises(ValueError):
                            require_transition(before, after)

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            require_transition("unknown", "ready")

    def test_ready_is_terminal(self):
        self.assertEqual(TRANSITIONS["ready"], set())

    def test_failed_cannot_publish(self):
        token = uuid4()
        self.assertFalse(owns_attempt("failed", token, token))

    def test_review_cannot_publish(self):
        token = uuid4()
        self.assertFalse(owns_attempt("needs_review", token, token))

    def test_processing_current_generation_can_publish(self):
        token = uuid4()
        self.assertTrue(owns_attempt("processing", token, token))

    def test_old_generation_cannot_publish(self):
        self.assertFalse(owns_attempt("processing", uuid4(), uuid4()))

    def test_missing_token_cannot_publish(self):
        self.assertFalse(owns_attempt("processing", None, None))

    def test_queued_cannot_publish(self):
        token = uuid4()
        self.assertFalse(owns_attempt("queued", token, token))

    def test_backoff_initial(self):
        self.assertEqual([dispatch_delay(n) for n in range(1, 7)], [5, 10, 20, 40, 80, 160])

    def test_backoff_bounded(self):
        for n in [7, 10, 100, 10**12]:
            self.assertEqual(dispatch_delay(n), 300)

    def test_backoff_bad_input(self):
        for n in [0, -1, True, False, 1.5, "1", None]:
            with self.subTest(n=n), self.assertRaises(ValueError):
                dispatch_delay(n)

    def recover(self, **changes):
        data = dict(state="needs_review", use_ai=False, has_file=False, confirmed=True, attempts=1)
        data.update(changes)
        return recovery_error(**data)

    def test_review_template_can_recover(self):
        self.assertIsNone(self.recover())

    def test_failed_template_can_recover(self):
        self.assertIsNone(self.recover(state="failed"))

    def test_ai_replay_refused(self):
        for state in ["failed", "needs_review"]:
            self.assertIsNotNone(self.recover(state=state, use_ai=True))

    def test_recovery_requires_confirmation(self):
        self.assertIsNotNone(self.recover(confirmed=False))

    def test_published_file_not_replaced(self):
        self.assertIsNotNone(self.recover(has_file=True))

    def test_active_or_ready_not_recovered(self):
        for state in ["queued", "processing", "ready", "unknown"]:
            with self.subTest(state=state):
                self.assertIsNotNone(self.recover(state=state))

    def test_recovery_limit(self):
        self.assertEqual(MAX_TEMPLATE_ATTEMPTS, 3)
        self.assertIsNone(self.recover(attempts=2))
        self.assertIsNotNone(self.recover(attempts=3))

    def test_stale_threshold_explicit(self):
        self.assertEqual(STALE_AFTER_SECONDS, 900)


if __name__ == "__main__":
    unittest.main()
