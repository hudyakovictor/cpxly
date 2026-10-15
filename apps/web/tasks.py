from celery import shared_task
from django.core.management import call_command


@shared_task
def clear_expired_sessions_task() -> None:
    """Clears stale expired sessions from the database."""
    call_command("clearsessions")


@shared_task
def infrastructure_echo_task(token: str) -> dict[str, str]:
    """Synthetic worker smoke only; not a product or AI integration."""
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_user")
        role = cursor.fetchone()[0]
    return {"token": token, "db_role": role}
