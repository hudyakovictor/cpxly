from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from apps.utils.ai_stub import analyze_synthetic


class AIStubTests(SimpleTestCase):
    @override_settings(AI_EXTERNAL_ENABLED=False)
    def test_no_network(self):
        with patch("socket.socket", side_effect=AssertionError("Network is prohibited")):
            self.assertEqual(analyze_synthetic("synthetic")["mode"], "synthetic-stub")

    @override_settings(AI_EXTERNAL_ENABLED=True)
    def test_external_ai_is_not_implemented(self):
        with self.assertRaises(RuntimeError):
            analyze_synthetic("synthetic")
