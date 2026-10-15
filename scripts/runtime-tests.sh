#!/bin/sh
set -eu
case "${COMPOSE_PROJECT_NAME:-}" in capexly-ci|capexly-ci-*) ;; *) echo 'Explicit disposable CI project required' >&2; exit 2;; esac
[ "${SECRETS_DIR:-}" = ./secrets/ci ] || { echo 'CI secrets required' >&2; exit 2; }
exec docker compose --env-file "${CAPEXLY_ENV_FILE:-.env.ci}" -f compose.yaml \
    run --pull never --rm -e DJANGO_SETTINGS_MODULE=project.settings_ci web python manage.py test --parallel 1 "$@"
