from .settings import *
from .infra_env import database, secret, storage

DEBUG = True
SECRET_KEY = secret("SECRET_KEY")
DATABASES = database()
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "web"]
CSRF_TRUSTED_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000"]
REDIS_URL = "redis://redis:6379/0"
CELERY_BROKER_URL = CELERY_RESULT_BACKEND = REDIS_URL
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "mailpit"
EMAIL_PORT = 1025
EMAIL_USE_TLS = False
EMAIL_USE_SSL = False
DEFAULT_FROM_EMAIL = "capexly@example.test"
STORAGES["default"] = storage()
STORAGES["default"]["BACKEND"] = "apps.utils.dev_storage.BrowserDevS3Storage"
S3_BROWSER_ENDPOINT = "http://localhost:3900"
AI_EXTERNAL_ENABLED = False
