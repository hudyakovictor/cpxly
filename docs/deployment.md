# Production deployment — candidate, not server-tested

Read STATUS.md. Production has no build section, runserver, source bind mounts,
frontend-dev or local Garage. Web/worker/beat use APP_IMAGE, the same approved image.
Migrations use that image with a separate role and secret.

## Before VPS connection
- Agree Linux amd64 VPS, DNS domain, resource sizing, private S3 and SMTP.
- Inspect diff, refresh dependency lock and run full CI/smoke acceptance.
- Populate separate production secret FILES; restrict host directory to owner.
  Compose secrets are files, not an encrypted vault. Docker/admin host access
  can read them. No Docker socket mounted into application containers.
- DOMAIN is one explicit hostname; no wildcard. HTTPS S3 endpoint and private
  bucket policy required. Signed URLs expire; do not expose object listing.
- Set production COMPOSE_PROJECT_NAME, SECRETS_DIR, APP_IMAGE and ACME_CA.
  Dev volumes/secrets must not be attached.

## Intended commands (not executed)
`APP_IMAGE=capexly-app:<release-id> make capexly-release-build`
Perform smoke-test before RELEASE_APPROVED=yes; successful build alone is insufficient.
`CAPEXLY_MODE=prod ./scripts/compose.sh config --quiet`
`CAPEXLY_MODE=prod ./scripts/compose.sh up -d --no-build --pull never db redis`
`CAPEXLY_MODE=prod make capexly-migrate`
`CAPEXLY_MODE=prod ./scripts/compose.sh up -d --no-build --pull never`

Public ports: Caddy TCP 80/443 only. DB/Redis/web are not published. Private
Docker networks enforce the proxy boundary. Caddy replaces scheme header.
Verify login/CSRF/redirects THROUGH Caddy, not only directly against Gunicorn.
Static: npm ci/build then collectstatic at build time, served by WhiteNoise.
Vite manifest is preserved; missing references must fail the build.

## TLS
Point DNS A/AAAA only at reachable server addresses. Allow inbound 80/443 and
outbound DNS/ACME; preserve Caddy /data and /config. Staging ACME is the default
example but requires explicit endpoint setting. Staging certificates are NOT
publicly trusted. Do not disable verification to pass a test.
Production CA availability not verified. Switch endpoint only after staging
issuance and review; distinguish issuance from trusted HTTPS acceptance.
Local prod-test with a dedicated CA is pending; do not alter host trust store.
For another CA, export CADDY_VARIANT=external-ca: the wrapper selects
compose.prod.external-ca.yaml INSTEAD of the ACME override. Supply
SECRETS_DIR/tls_certificate.pem and tls_key.pem; only Caddy mounts them.
Renew before expiry; app containers never receive the key.
Diagnosis: `./scripts/compose.sh logs --tail=100 caddy` (redact sensitive output),
DNS/firewall checks; certificate expiry with `openssl s_client`/`openssl x509`
on an approved environment. Alert on renewal errors and impending expiry.
Healthcheck marks unhealthy; restart policy does not restart on that status.
Monitoring/alert destination must be selected before actual server deployment.

## Release transfer and rollback
`CAPEXLY_MODE=prod RELEASE_ID=<release-id> RELEASE_APPROVED=yes ./scripts/release-save.sh release.tar`
Packaging requires capexly-tooling locally; it is not a server service.
Transfer tar, sha256, .ids, .sources and .compose.yaml over an approved authenticated channel.
Use independent clean Docker environment: `./scripts/release-load.sh release.tar`;
verify each local image architecture and run with `RELEASE_OVERRIDE=./release.tar.compose.yaml`
and `--no-build --pull never`. Use the override on ALL subsequent commands.
Archive uses unique local release tags plus verified image IDs because save/load
does not necessarily preserve original repository digest associations.
Changing Compose project name is NOT a clean image-cache test. Do not erase
an existing daemon; use a separate authorized machine/daemon.
No export/import, secrets, documents or volumes in image archive.
Keep previous approved image/archive and release metadata. Image rollback does
not undo schema migrations; check compatibility or restore coherent DB+objects.
Registry is optional: later select one, confirm access policy and immutable
references, push approved images, test pull; no paid registry is required now.

## Controlled updates
Update image tags/digests only from official manifests after vulnerability and
architecture review. Update uv.lock/package-lock in explicit change, run CI,
static/auth/runtime-role/backup/transfer tests, and approve a new immutable release.
No apt-get install in the app build: psycopg[binary] is used in both dev and
prod. Existing lock has cp314 manylinux amd64 wheel 3.3.4; update lock for the
changed extras and test. Bundled libpq/OpenSSL updates require controlled wheel
updates and release tests, not implicit host package upgrades.

## Supplementary review notes
Read review-packet.md for exact role/secret/deployment changes. For verified
certificate-expiry checks run scripts/tls-check.py inside an approved image
with TLS_CHECK_HOST; it verifies trust and hostname. ACME staging is expected
to fail default public trust validation; do not bypass TLS to mark it passed.
Lint/type-check/full layer-secret audit have NOT been executed here.
Monitoring/alert destination, retention/encryption and real provider policies
remain operational decisions before actual production use.

## Release source / single-platform archive gate
release-build.sh rejects a dirty tree and existing release tags, checks lock,
and labels the image with committed source revision. After tests/review,
release-save.sh requires the same clean source/config revision as the image.
Gunicorn access log omits path/query strings to avoid logging URL tokens.

Archive commands use --platform=linux/amd64 explicitly. Docker save defaults
to ALL variants in the local store, so inspect-only is insufficient. The chosen
inspect --platform option requires API >=1.49; save/load filtering API >=1.48.
For this pipeline, client/server must support API >=1.49 and these options.
An older Docker is a BLOCKER, not permission to upgrade OS or weaken the check.
Sources: https://docs.docker.com/reference/cli/docker/image/save/
and https://docs.docker.com/reference/cli/docker/image/inspect/

Compose/Caddy/init-check SQL/host scripts and docs must also be transferred as
reviewed configuration from the SAME source revision, without env/keys/backups.
Image save archive is not a substitute for this config handoff; server never
builds the app from that source. Register actual image ID, revision and test
evidence before deployment. Keep previous matching configuration for rollback.
