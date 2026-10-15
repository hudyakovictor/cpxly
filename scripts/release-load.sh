#!/bin/sh
set -eu
archive=${1:?archive path required}
(cd "$(dirname "$archive")" && sha256sum -c "$(basename "$archive").sha256")
docker image load --platform=linux/amd64 -i "$archive"
while read -r expected image; do
    [ "$(docker image inspect --platform=linux/amd64 --format '{{.Id}}' "$image")" = "$expected" ] || { echo 'Loaded image identity mismatch' >&2; exit 2; }
    [ "$(docker image inspect --platform=linux/amd64 --format '{{.Os}}/{{.Architecture}}' "$image")" = linux/amd64 ] || { echo 'Wrong architecture' >&2; exit 2; }
done < "$archive.ids"
echo 'Use RELEASE_OVERRIDE=archive.compose.yaml with --no-build --pull never; run clean-environment smoke test.'
