from .settings_build import *
from .infra_env import database

DATABASES = database()
ALLOWED_HOSTS = ["testserver", "localhost"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
STORAGES["default"] = {"BACKEND": "django.core.files.storage.InMemoryStorage"}
STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}
TEST_RUNNER = "apps.utils.runtime_test_runner.PreparedDatabaseRunner"
RUN_RUNTIME_ACCESS_TESTS = True
AI_EXTERNAL_ENABLED = False
