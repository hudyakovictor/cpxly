"""Explicit trusted-code registry; never import Python paths from database input.

S-03 has a synthetic draft handler. Other entries remain metadata only.
Activation is separately gated; a code registry is not proof of runtime readiness.
"""
from collections.abc import Callable
from typing import Any

from apps.selfservice.claim_engine import build_draft

_HANDLERS: dict[str, Callable[..., Any]] = {"S-03": build_draft}


def has_handler(code: str) -> bool:
    return callable(_HANDLERS.get(code))


def require_handler(code: str) -> Callable[..., Any]:
    handler = _HANDLERS.get(code)
    if not callable(handler):
        raise NotImplementedError("Service handler is not connected")
    return handler
