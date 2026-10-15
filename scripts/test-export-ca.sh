#!/bin/sh
set -eu
[ "${CAPEXLY_MODE:-}" = prod-test ] || { echo 'Only prod-test allowed' >&2; exit 2; }
case "${SECRETS_DIR:-}" in ./secrets/prod-test|./secrets/restore-test) ;; *) echo 'Test secrets dir required' >&2; exit 2;; esac
# Export ONLY public root certificate, never private CA keys or host trust.
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
./scripts/compose.sh exec -T caddy cat /data/caddy/pki/authorities/local/root.crt > "$tmp"
test -s "$tmp" || { echo 'No local test CA certificate yet' >&2; exit 2; }
chmod 444 "$tmp"
mv "$tmp" "$SECRETS_DIR/test_ca.crt"
echo 'Public local-test CA exported. Host/system trust store NOT changed.'
