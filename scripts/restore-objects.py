import hashlib
import json
import os
from pathlib import Path
import boto3
from botocore.config import Config
import django

django.setup()
from django.conf import settings
if os.environ.get("RESTORE_INTO_EMPTY_ENVIRONMENT") != "yes":
    raise SystemExit("Explicit isolated-empty-environment confirmation required")
root=Path(os.environ["BACKUP_DIR"])
o=settings.STORAGES["default"]["OPTIONS"]
s3=boto3.client("s3", endpoint_url=o["endpoint_url"], region_name=o["region_name"], aws_access_key_id=o["access_key"], aws_secret_access_key=o["secret_key"], verify=o["verify"], config=Config(signature_version="s3v4", s3={"addressing_style": "path"}))
if s3.list_objects_v2(Bucket=o["bucket_name"],MaxKeys=1).get("KeyCount",0):
    raise SystemExit("Target bucket must be empty")
items=json.loads((root/"manifest.json").read_text())
for item in items:
    allowed_metadata = {"Metadata", "ContentDisposition", "ContentEncoding", "CacheControl", "ContentLanguage"}
    if set(item.get("metadata", {})) - allowed_metadata:
        raise SystemExit("Unsupported backup metadata fields")
    name=item["file"]
    if Path(name).name != name:
        raise SystemExit("Unsafe backup path")
    p=root/name
    with p.open("rb") as f:
        if hashlib.file_digest(f,"sha256").hexdigest()!=item["sha256"]:
            raise SystemExit("Checksum mismatch")
# Verify all input checksums before any writes.
for item in items:
    with (root/item["file"]).open("rb") as f:
        s3.put_object(Bucket=o["bucket_name"],Key=item["key"],Body=f,ContentType=item["content_type"], **item.get("metadata", {}))
    body=s3.get_object(Bucket=o["bucket_name"],Key=item["key"])["Body"]
    sha=hashlib.sha256()
    for chunk in body.iter_chunks(1024*1024):sha.update(chunk)
    if sha.hexdigest()!=item["sha256"]:raise SystemExit("Restored object mismatch")
print(f"Restored and hash-checked {len(items)} objects; DB-to-file links require a separate application check")
