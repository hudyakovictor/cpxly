"""Infrastructure-only settings. Secrets are runtime-mounted, never build args."""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured


def secret(name):
    path = os.environ.get(f"{name}_FILE")
    if not path:
        raise ImproperlyConfigured(f"{name}_FILE must reference a runtime secret")
    value = Path(path).read_text().strip()
    if not value:
        raise ImproperlyConfigured(f"{name} cannot be empty")
    return value


def database():
    return {"default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": "db", "PORT": "5432", "NAME": "capexly",
        "USER": os.environ.get("DB_USER", "capexly_runtime"),
        "PASSWORD": secret("DB_PASSWORD"),
    }}


def storage():
    return {"BACKEND": "storages.backends.s3.S3Storage", "OPTIONS": {
        "access_key": secret("S3_ACCESS_KEY"),
        "secret_key": secret("S3_SECRET_KEY"),
        "bucket_name": os.environ["S3_BUCKET"],
        "region_name": os.environ.get("S3_REGION", "us-east-1"),
        "endpoint_url": os.environ.get("S3_ENDPOINT_URL") or None,
        "default_acl": None, "querystring_auth": True,
        "querystring_expire": 300, "file_overwrite": False,
        "custom_domain": None, "verify": True,
        "signature_version": "s3v4", "addressing_style": "path",
    }}
