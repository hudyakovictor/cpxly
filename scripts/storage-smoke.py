"""Synthetic S3 test, run only in the dev migrate container.
Uploads a NEW uniquely named object. Deliberately retains it for restart and
backup/restore checks; no destructive cleanup is performed.
"""
import hashlib
import http.client
import os
import uuid
from urllib.parse import urlsplit
import django

django.setup()
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

if settings.SETTINGS_MODULE not in ("project.settings_container_dev", "project.settings_prod_test"):
    raise SystemExit("Run only with isolated synthetic development settings")
expected=b"capexly synthetic private-storage smoke test\n"
name=default_storage.save("infra-smoke/"+uuid.uuid4().hex+".txt",ContentFile(expected))
with default_storage.open(name,"rb") as f:
    if f.read()!=expected: raise SystemExit("Signed SDK read mismatch")
url=default_storage.url(name)
u=urlsplit(url)
expected_port = 3901 if settings.SETTINGS_MODULE == "project.settings_prod_test" else 3900
if u.hostname != "localhost" or u.port != expected_port or not u.query:
    raise SystemExit("Incorrect browser signing endpoint")
# Connect via container DNS but preserve signed browser Host; no TLS bypass.
conn=http.client.HTTPConnection("garage",3900,timeout=10)
conn.request("GET",u.path+"?"+u.query,headers={"Host":u.netloc})
resp=conn.getresponse();body=resp.read()
if resp.status!=200 or body!=expected:raise SystemExit("Presigned GET failed")
conn.close()
conn=http.client.HTTPConnection("garage",3900,timeout=10)
conn.request("GET",u.path,headers={"Host":u.netloc})
resp=conn.getresponse();resp.read()
if resp.status!=403:raise SystemExit("Anonymous GET must return 403")
conn.close()
# Do not print credential-bearing URLs or keys; show only synthetic object hash.
print("PASS SDK upload/read; presigned GET=200; anonymous GET=403")
print("Synthetic object SHA256:",hashlib.sha256(expected).hexdigest())
print("Object retained for persistence/backup checks; smoke-test not recovery proof.")
