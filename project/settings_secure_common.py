# Added by Capexly. Shared secure runtime configuration, not build/dev settings.
import os
import re
from django.core.exceptions import ImproperlyConfigured

# Must be set before .settings decides whether to install browser-reload.
os.environ["DEBUG"] = "False"
os.environ["DJANGO_VITE_DEV_MODE"] = "False"
from .settings import *
from .infra_env import database, secret, storage

DEBUG = False
SECRET_KEY = secret("SECRET_KEY")
DATABASES = database()
DOMAIN = os.environ.get("DOMAIN", "").strip()
if not re.fullmatch(r"(?=.{1,253}\Z)[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", DOMAIN):
    raise ImproperlyConfigured("DOMAIN must be a single explicit hostname")
ALLOWED_HOSTS = [DOMAIN]
CSRF_TRUSTED_ORIGINS = [f"https://{DOMAIN}"]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = False
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
USE_HTTPS_IN_ABSOLUTE_URLS = True
DJANGO_VITE["default"]["dev_mode"] = False
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STORAGES["staticfiles"] = {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}
STORAGES["default"] = storage()
REDIS_URL = "redis://redis:6379/0"
CELERY_BROKER_URL = CELERY_RESULT_BACKEND = REDIS_URL
CACHES["default"] = {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL}
AI_EXTERNAL_ENABLED = False
CELERY_TASK_ALWAYS_EAGER = False
