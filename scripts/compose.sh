#!/bin/sh
set -eu
mode=${CAPEXLY_MODE:-dev}
case "$mode" in dev|prod|prod-test) ;; *) echo 'CAPEXLY_MODE must be dev/prod/prod-test' >&2; exit 2;; esac
if [ "$mode" = prod-test ]; then
    case "${COMPOSE_PROJECT_NAME:-}" in capexly-test-*|capexly-restore-*) ;; *) echo 'Explicit isolated test project name required' >&2; exit 2;; esac
    case "${SECRETS_DIR:-}" in ./secrets/prod-test|./secrets/restore-test) ;; *) echo 'Only separate synthetic test secrets allowed' >&2; exit 2;; esac
fi
override="compose.$mode.yaml"
if [ "$mode" = prod ]; then
    case "${CADDY_VARIANT:-acme}" in
        acme) ;;
        external-ca) override=compose.prod.external-ca.yaml ;;
        *) echo 'Unknown CADDY_VARIANT' >&2; exit 2;;
    esac
fi
if [ -n "${RELEASE_OVERRIDE:-}" ]; then
    exec docker compose --env-file "${CAPEXLY_ENV_FILE:-.env}" -f compose.yaml -f "$override" -f "$RELEASE_OVERRIDE" "$@"
fi
exec docker compose --env-file "${CAPEXLY_ENV_FILE:-.env}" -f compose.yaml -f "$override" "$@"
