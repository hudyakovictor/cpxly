"""Pure decision rules. Passing these tests does not prove DB/broker behaviour."""
MAX_TEMPLATE_ATTEMPTS = 3
STALE_AFTER_SECONDS = 15 * 60
TRANSITIONS = {
    "queued": {"processing", "failed", "needs_review"},
    "processing": {"ready", "failed", "needs_review"},
    "failed": {"queued"},
    "needs_review": {"queued"},
    "ready": set(),
}


def require_transition(before, after):
    if after not in TRANSITIONS.get(before, set()):
        raise ValueError("Invalid request state transition")


def owns_attempt(state, actual_token, expected_token):
    return state == "processing" and bool(actual_token) and actual_token == expected_token


def dispatch_delay(attempt):
    if type(attempt) is not int or attempt < 1:
        raise ValueError("Attempt must be a positive integer")
    return min(300, 5 * (2 ** min(attempt - 1, 6)))


def recovery_error(*, state, use_ai, has_file, confirmed, attempts):
    if not confirmed:
        return "Требуется явное подтверждение повторной шаблонной обработки"
    if use_ai:
        return "Заявка с внешним ИИ не повторяется: сначала сверить вызов и расходы провайдера"
    if state not in {"failed", "needs_review"}:
        return "Повтор разрешён только для failed/needs_review, не для активной или готовой заявки"
    if has_file:
        return "У заявки уже есть опубликованный файл; восстановление не должно его заменять"
    if attempts >= MAX_TEMPLATE_ATTEMPTS:
        return "Лимит обработок исчерпан; требуется отдельная диагностика"
    return None
