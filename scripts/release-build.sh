#!/bin/sh
set -eu
image=${APP_IMAGE:?Unique release APP_IMAGE tag required}
case "$image" in *:latest|*:dev|*:ci|*REPLACE*|*@*) echo 'Use a unique explicit release tag, not latest/dev/ci/digest placeholder' >&2; exit 2;; esac
case "$image" in *:*) ;; *) echo 'Explicit release tag required' >&2; exit 2;; esac
[ -z "$(git status --porcelain)" ] || { echo 'Release build requires reviewed committed source; working tree is dirty' >&2; exit 2; }
if docker image inspect "$image" >/dev/null 2>&1; then
    echo 'Release tag already exists; refusing implicit overwrite' >&2
    exit 2
fi
revision=$(git rev-parse HEAD)
docker run --rm -v "$PWD:/app:ro" capexly-tooling uv lock --check
docker buildx build --platform linux/amd64 --target production --load \
    --label "org.opencontainers.image.revision=$revision" -t "$image" .
echo 'Release image built from clean committed source. Build is NOT smoke/acceptance success.'
