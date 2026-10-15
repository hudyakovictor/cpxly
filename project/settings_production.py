# Production-only provider configuration. No insecure endpoint exception.
import os
from django.core.exceptions import ImproperlyConfigured
from .settings_secure_common import *

S3_ENDPOINT = os.environ.get("S3_ENDPOINT_URL", "")
if S3_ENDPOINT and not S3_ENDPOINT.startswith("https://"):
    raise ImproperlyConfigured("Production S3 endpoint must use HTTPS")
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("SMTP_HOST", "")
EMAIL_PORT = int(os.environ.get("SMTP_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("SMTP_USER", "")
EMAIL_HOST_PASSWORD = secret("SMTP_PASSWORD")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "")
if not EMAIL_HOST or not DEFAULT_FROM_EMAIL:
    raise ImproperlyConfigured("Production SMTP_HOST and DEFAULT_FROM_EMAIL required")
