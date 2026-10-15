#!/bin/sh
set -eu
archive=${1:?dump path required}
[ "${RESTORE_INTO_EMPTY_ENVIRONMENT:-}" = yes ] || { echo 'Restore only into a new isolated environment; explicit confirmation required' >&2; exit 2; }
(cd "$(dirname "$archive")" && sha256sum -c "$(basename "$archive").sha256")
# No --clean, DROP DATABASE, or volume deletion. Existing objects cause failure.
./scripts/compose.sh run --pull never --rm -T db-ops 'export PGPASSWORD="$(cat /run/secrets/db_migrator_password)"; exec pg_restore --exit-on-error --single-transaction --no-owner --no-acl -d capexly' < "$archive"
./scripts/compose.sh run --pull never --rm db-ops
