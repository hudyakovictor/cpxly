#!/bin/sh
set -eu
archive=${1:?archive path required}
release=${RELEASE_ID:?Unique immutable release identifier required}
case "$release" in *[!a-zA-Z0-9_.-]*|'') echo 'Invalid RELEASE_ID' >&2; exit 2;; esac
for file in "$archive" "$archive.sources" "$archive.ids" "$archive.compose.yaml" "$archive.sha256"; do
    test ! -e "$file" || { echo 'Refusing to overwrite release artifacts' >&2; exit 2; }
done
case "${CAPEXLY_MODE:-}" in prod|prod-test) ;; *) echo 'Use prod or isolated prod-test' >&2; exit 2;; esac
[ "${RELEASE_APPROVED:-}" = yes ] || { echo 'RELEASE_APPROVED=yes requires documented acceptance' >&2; exit 2; }
[ -z "${RELEASE_OVERRIDE:-}" ] || { echo 'Package from original approved config' >&2; exit 2; }
[ -z "$(git status --porcelain)" ] || { echo 'Dirty source/config tree cannot be packaged' >&2; exit 2; }
revision=$(git rev-parse HEAD)
[ "$(docker image inspect --platform=linux/amd64 --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "${APP_IMAGE:?}")" = "$revision" ] || { echo 'Image revision differs from reviewed configuration' >&2; exit 2; }
# Extract only image references; expanded config is never logged/persisted.
./scripts/compose.sh --profile '*' config --format json | docker run --rm -i capexly-tooling python -c 'import sys,json; c=json.load(sys.stdin); [print(k+" "+v["image"]) for k,v in c["services"].items()]' > "$archive.sources"
test -s "$archive.sources" || { echo 'No image manifest generated' >&2; exit 2; }
: > "$archive.ids"
printf 'services:\n' > "$archive.compose.yaml"
refs=''
while read -r service image; do
    [ "$(docker image inspect --platform=linux/amd64 --format '{{.Os}}/{{.Architecture}}' "$image")" = linux/amd64 ] || { echo 'Wrong architecture' >&2; exit 2; }
    id=$(docker image inspect --platform=linux/amd64 --format '{{.Id}}' "$image")
    ref="capexly-release/$service:$release"
    if docker image inspect "$ref" >/dev/null 2>&1; then
        [ "$(docker image inspect --platform=linux/amd64 --format '{{.Id}}' "$ref")" = "$id" ] || { echo 'Refusing release tag overwrite' >&2; exit 2; }
    fi
    docker image tag "$image" "$ref"
    printf '%s %s\n' "$id" "$ref" >> "$archive.ids"
    printf '  %s:\n    image: %s\n    pull_policy: never\n' "$service" "$ref" >> "$archive.compose.yaml"
    refs="$refs $ref"
done < "$archive.sources"
# save/load preserves config/layers, not necessarily repository digest aliases.
docker image save --platform=linux/amd64 -o "$archive" $refs
(cd "$(dirname "$archive")" && sha256sum "$(basename "$archive")" "$(basename "$archive").ids" "$(basename "$archive").compose.yaml" "$(basename "$archive").sources" > "$(basename "$archive").sha256")
echo 'Archive created; clean-environment offline startup remains to be tested.'
