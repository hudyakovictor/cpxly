#!/bin/sh
set -eu
bundle=${1:?backup-set path required}
[ "${RESTORE_INTO_EMPTY_ENVIRONMENT:-}" = yes ] || { echo 'Confirm empty isolated destination first' >&2; exit 2; }
[ "${CAPEXLY_MODE:-}" = prod-test ] || { echo 'Automated restore-set is limited to synthetic prod-test' >&2; exit 2; }
case "${COMPOSE_PROJECT_NAME:-}" in capexly-restore-*) ;; *) echo 'Use a dedicated restore project' >&2; exit 2;; esac
[ "${SECRETS_DIR:-}" = ./secrets/restore-test ] || { echo 'Dedicated restore secrets required' >&2; exit 2; }
case "$bundle" in /*) ;; *) echo 'Backup path must be absolute' >&2; exit 2;; esac
(cd "$bundle" && sha256sum -c SHA256SUMS)
# Initialize only empty DB roles and private bucket; do NOT migrate before restore.
./scripts/compose.sh up -d --wait db redis garage mailpit
objects=$(./scripts/compose.sh run --pull never --rm -T db-ops 'export PGPASSWORD="$(cat /run/secrets/db_migrator_password)"; exec psql -At -v ON_ERROR_STOP=1 -f /checks/check-empty.sql')
[ "$objects" = 0 ] || { echo 'Destination database is not empty; refusing restore' >&2; exit 2; }
./scripts/restore-db.sh "$bundle/db.dump"
./scripts/compose.sh run --pull never --rm --user "$(id -u):$(id -g)" \
    -v "$bundle:/backup:ro" -e BACKUP_DIR=/backup/objects \
    -e RESTORE_INTO_EMPTY_ENVIRONMENT=yes migrate python scripts/restore-objects.py
./scripts/compose.sh run --pull never --rm synthetic python scripts/synthetic-fixture.py verify
echo 'Synthetic DB/file-link verification executed; keep output as recovery evidence.'
