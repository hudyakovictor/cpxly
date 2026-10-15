#!/bin/sh
set -eu
root=${BACKUP_ROOT:?Absolute path on approved separate storage required}
name=${BACKUP_SET_ID:?Unique backup-set identifier required}
case "$root" in /*) ;; *) echo 'BACKUP_ROOT must be absolute' >&2; exit 2;; esac
case "$name" in *[!a-zA-Z0-9_.-]*|'') echo 'Invalid set ID' >&2; exit 2;; esac
[ "${CONFIRM_PAUSE_WRITES:-}" = yes ] || { echo 'CONFIRM_PAUSE_WRITES=yes required' >&2; exit 2; }
[ "${BACKUP_SEPARATE_STORAGE_CONFIRMED:-}" = yes ] || { echo 'Approve separate backup storage first' >&2; exit 2; }
if [ "${CAPEXLY_MODE:-dev}" = prod ]; then
    [ "${OFFSERVER_BACKUP_TARGET_CONFIRMED:-}" = yes ] || { echo 'Off-server restricted/encrypted target must be confirmed' >&2; exit 2; }
fi
bundle="$root/$name"
umask 077
mkdir "$bundle" # Refuses to overwrite an existing recovery set.
./scripts/compose.sh stop web worker beat
export WRITES_QUIESCED=yes
# Operator must also stop any non-application writers.
./scripts/backup-db.sh "$bundle/db.dump"
./scripts/compose.sh run --pull never --rm --user "$(id -u):$(id -g)" \
    -v "$bundle:/backup" -e BACKUP_DIR=/backup/objects \
    -e WRITES_QUIESCED=yes -e BACKUP_SEPARATE_STORAGE_CONFIRMED=yes \
    migrate python scripts/backup-objects.py
./scripts/compose.sh config --images | sort -u > "$bundle/images.txt"
(cd "$bundle" && find . -type f ! -name SHA256SUMS -exec sha256sum {} + > SHA256SUMS)
echo 'Recovery set created; writers remain stopped. Verify/check off-server copy, then explicitly start web/worker/beat.'
echo 'This is not proof of successful restore, encryption, or off-server transport.'
