# Development S3 decision: Garage 2.4.1

Scope: replaces MinIO in synthetic dev and future isolated prod-test only.
Production remains an external PRIVATE S3 service. No provider account created.

Why Garage: documented single-node mode, automatic private bucket/key bootstrap,
SigV4, path-style requests, presigned URLs, separate persistent metadata/data.
Official quick start explicitly references dxflrs/garage:v2.4.1. Anonymous
registry access returned 200, multiarch index contains linux/amd64 and arm64.
Immutable reference and per-platform digest are in infra/images.lock.json.

License verified from official v2.4.1 LICENSE: GNU AGPL v3. This is a separate,
unmodified dev service, not a library linked into Django. Preserve its notices
and source link when redistributing. This is not a legal conclusion about all
possible distribution/modification scenarios; review obligations before those.

RustFS was considered: Apache-2.0, official Docker image also accessible with
amd64. It is not rejected as nonviable; Garage was selected for its documented
single-node bootstrap for this narrow local test. LocalStack is not needed as
a general AWS emulator. No marketing performance/compliance claims adopted.

IMPORTANT: Garage does not implement AWS ACL/bucket policy APIs. Bucket rights
are Garage-specific, per key and per bucket. The dev adapter sets default_acl=None;
no PutObjectAcl or bucket-policy bootstrap. Production cloud policy/ACL/region,
TLS and multipart behavior MUST be tested against the selected real provider.
A successful Garage test cannot certify production S3 compatibility.

Files changed for storage: compose.dev.yaml, infra/garage/*, images.lock.json,
.env.example, dev-secrets.py, infra_env.py, settings_container_dev.py,
apps/utils/dev_storage.py, scripts/storage-smoke.py and local documentation.

Ports: localhost:3900 only. RPC loopback-only; no web/admin API enabled or
published. Named volumes garage_meta/garage_data survive normal stop/down.
Garage runs as root ONLY inside dev storage container for its own named-volume
initialization, cap_drop ALL, read-only rootfs, no privileged mode/socket or host
data mounts. Application production USER remains 10001:10001. Review this local
storage choice separately if requiring a non-root storage daemon too.

Secret mounts: application S3 key pair plus Garage-only RPC secret. Wrapper
reads files and execs Garage; values never baked into image ENV/ARG or printed.
The default key has dev bucket rights; it is not a cloud production credential.
Bootstrap existing volumes never rotated blindly: coordinate a key rotation if
secret files change; do not delete volumes or overwrite keys automatically.

Verification status:
- Official docs/license checked; manifest/config access checked anonymously.
- Image layer download/checksum evidence is separate in image-download-check.json.
- Docker pull, container start, health, private upload/403/presigned GET, persistence
  and restore are NOT RUN: Docker is absent in the current environment.
- Candidate storage-smoke command is written, not passed.

Sources:
https://garagehq.deuxfleurs.fr/documentation/quick-start/
https://garagehq.deuxfleurs.fr/documentation/reference-manual/configuration/
https://garagehq.deuxfleurs.fr/documentation/reference-manual/s3-compatibility/
https://git.deuxfleurs.fr/Deuxfleurs/garage/raw/tag/v2.4.1/LICENSE
https://github.com/rustfs/rustfs
