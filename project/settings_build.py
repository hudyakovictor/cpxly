# Build-only, no network services or deployment secrets required by collectstatic.
import os
os.environ["DEBUG"] = "False"
from .settings import *
DEBUG = False
SECRET_KEY = "build-only-not-valid-for-runtime"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
DJANGO_VITE["default"]["dev_mode"] = False
STORAGES["staticfiles"] = {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}
