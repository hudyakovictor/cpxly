# Explicit local-only synthetic harness; NOT production provider validation.
import os
from django.core.exceptions import ImproperlyConfigured
from .settings_secure_common import *

if os.environ.get("CAPEXLY_SYNTHETIC_TEST") != "1" or DOMAIN != "capexly.test":
    raise ImproperlyConfigured("Isolated prod-test settings require capexly.test")
if os.environ.get("S3_ENDPOINT_URL") != "http://garage:3900":
    raise ImproperlyConfigured("Prod-test may only use its isolated Garage endpoint")
CSRF_TRUSTED_ORIGINS = ["https://capexly.test", "https://capexly.test:8443"]
STORAGES["default"]["BACKEND"] = "apps.utils.dev_storage.BrowserDevS3Storage"
S3_BROWSER_ENDPOINT = "http://localhost:3901"
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "mailpit"
EMAIL_PORT = 1025
EMAIL_HOST_USER = EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = "capexly@example.test"
