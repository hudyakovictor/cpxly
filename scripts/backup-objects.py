"""Run inside the migrate container, with a separately mounted backup directory.
Writes must remain stopped through both DB and object backup. Uses the same
S3 configuration as Django; manifests contain object names and hashes, not keys.
"""
import hashlib
import json
import os
from pathlib import Path
import boto3
from botocore.config import Config
import django

django.setup()
from django.conf import settings

os.umask(0o077)
root = Path(os.environ["BACKUP_DIR"])
if os.environ.get("WRITES_QUIESCED") != "yes" or os.environ.get("BACKUP_SEPARATE_STORAGE_CONFIRMED") != "yes":
    raise SystemExit("Quiesced writes and separate storage confirmation required")
root.mkdir(parents=True, exist_ok=False)
o = settings.STORAGES["default"]["OPTIONS"]
s3 = boto3.client("s3", endpoint_url=o["endpoint_url"], region_name=o["region_name"], aws_access_key_id=o["access_key"], aws_secret_access_key=o["secret_key"], verify=o["verify"], config=Config(signature_version="s3v4", s3={"addressing_style": "path"}))
manifest=[]
for page in s3.get_paginator("list_objects_v2").paginate(Bucket=o["bucket_name"]):
    for obj in page.get("Contents", []):
        key=obj["Key"]
        filename=f"{len(manifest):08d}.object"
        response=s3.get_object(Bucket=o["bucket_name"], Key=key)
        sha=hashlib.sha256()
        with (root/filename).open("xb") as f:
            for chunk in response["Body"].iter_chunks(1024*1024):
                sha.update(chunk); f.write(chunk)
        manifest.append({"key":key,"file":filename,"sha256":sha.hexdigest(),"content_type":response.get("ContentType","application/octet-stream"), "metadata": {k:response[k] for k in ("Metadata", "ContentDisposition", "ContentEncoding", "CacheControl", "ContentLanguage") if k in response}})
(root/"manifest.json").write_text(json.dumps(manifest,indent=2))
print(f"Backed up {len(manifest)} objects; restored links have not yet been checked")
