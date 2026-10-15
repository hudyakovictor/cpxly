"""No provider SDK or network transport is available in this adapter."""
from django.conf import settings


def analyze_synthetic(text):
    if getattr(settings, "AI_EXTERNAL_ENABLED", False):
        raise RuntimeError("External AI integration is not implemented")
    return {"mode": "synthetic-stub", "characters": len(text), "result": None}
