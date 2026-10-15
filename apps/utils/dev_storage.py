"""Dev-only signing endpoint: browser localhost differs from Docker service DNS.
Never rewrite a signed URL after signing; the Host is part of SigV4.
"""
from django.conf import settings
from storages.backends.s3 import S3Storage
from storages.utils import clean_name
import boto3
from botocore.config import Config


class BrowserDevS3Storage(S3Storage):
    def url(self, name, parameters=None, expire=None, http_method=None):
        name = self._normalize_name(clean_name(name))
        client = boto3.client(
            "s3", endpoint_url=settings.S3_BROWSER_ENDPOINT,
            region_name=self.region_name, aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
        params = {"Bucket": self.bucket_name, "Key": name}
        params.update(parameters or {})
        return client.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=expire or self.querystring_expire,
            HttpMethod=http_method or "GET",
        )
