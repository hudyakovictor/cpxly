#!/bin/sh
set -eu
out=${1:?path on separately mounted backup storage required}
[ "${WRITES_QUIESCED:-}" = yes ] || { echo 'Stop all writers, then confirm WRITES_QUIESCED=yes' >&2; exit 2; }
[ "${BACKUP_SEPARATE_STORAGE_CONFIRMED:-}" = yes ] || { echo 'Confirm separate storage' >&2; exit 2; }
test ! -e "$out" && test ! -e "$out.partial" || { echo 'Refusing overwrite' >&2; exit 2; }
umask 077
./scripts/compose.sh run --pull never --rm -T db-ops 'export PGPASSWORD="$(cat /run/secrets/db_migrator_password)"; exec pg_dump -Fc --no-owner --no-acl' > "$out.partial"
mv "$out.partial" "$out"
(cd "$(dirname "$out")" && sha256sum "$(basename "$out")" > "$(basename "$out").sha256")
echo 'Database dump created; complete backup also requires object snapshot and recovery manifest.'
