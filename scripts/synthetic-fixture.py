"""Synthetic infrastructure data only; never permitted in actual production."""
import base64
import hashlib
import os
import sys
from pathlib import Path
import django

django.setup()
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from apps.users.models import CustomUser
from apps.web.tasks import infrastructure_echo_task

if settings.SETTINGS_MODULE != "project.settings_prod_test":
    raise SystemExit("Only isolated prod-test settings allowed")
password = Path(os.environ["SMOKE_PASSWORD_FILE"]).read_text().strip()
email = "infra-synthetic@example.test"
# A tiny synthetic PNG, no customer document.
payload = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a3ioAAAAASUVORK5CYII="
)
mode = sys.argv[1] if len(sys.argv) > 1 else "verify"
if mode not in ("prepare", "verify"):
    raise SystemExit("Use prepare or verify")
if mode == "prepare":
    user, created = CustomUser.objects.get_or_create(username=email, defaults={"email": email})
    if created:
        user.set_password(password)
        user.avatar.save("synthetic.png", ContentFile(payload), save=False)
        user.save()
    elif not user.check_password(password):
        raise SystemExit("Existing synthetic user password differs; no overwrite performed")
    send_mail("Capexly synthetic infrastructure smoke", "Synthetic test only", settings.DEFAULT_FROM_EMAIL, [email])
else:
    user = CustomUser.objects.get(username=email)
    # Restore uses different secrets; original password is deliberately not changed.
with user.avatar.open("rb") as f:
    actual = f.read()
if hashlib.sha256(actual).digest() != hashlib.sha256(payload).digest():
    raise SystemExit("Restored/stored DB-to-file link or file content mismatch")
if mode == "prepare":
    token = "synthetic-worker-check"
    result = infrastructure_echo_task.delay(token).get(timeout=60)
    if result != {"token": token, "db_role": "capexly_runtime"}:
        raise SystemExit("Worker result mismatch")
    print("PASS synthetic user/file link; SMTP send accepted; separate worker result received")
else:
    print("PASS persisted/restored synthetic DB-to-file link and content hash")
