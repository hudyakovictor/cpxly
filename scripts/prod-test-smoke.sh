#!/bin/sh
set -eu
[ "${CAPEXLY_MODE:-}" = prod-test ] || { echo 'Only isolated prod-test allowed' >&2; exit 2; }
./scripts/compose.sh config --quiet
# Approved release image must already exist. This never builds the application.
./scripts/compose.sh up -d --wait --no-build --pull never db redis garage mailpit
./scripts/compose.sh run --pull never --rm --no-deps migrate
./scripts/compose.sh run --pull never --rm db-ops
./scripts/compose.sh up -d --wait --no-build --pull never web worker beat caddy
for n in $(seq 1 30); do
    if ./scripts/test-export-ca.sh; then break; fi
    sleep 2
    [ "$n" != 30 ] || exit 1
done
./scripts/compose.sh run --pull never --rm synthetic python scripts/storage-smoke.py
./scripts/compose.sh run --pull never --rm synthetic python scripts/synthetic-fixture.py prepare
./scripts/compose.sh run --pull never --rm probe
count=$(./scripts/compose.sh ps -q beat | wc -l | tr -d ' ')
[ "$count" = 1 ] || { echo 'Exactly one beat required' >&2; exit 2; }
if [ "${CONFIRM_RESTART_SYNTHETIC:-}" = yes ]; then
    ./scripts/compose.sh restart db redis garage web worker beat
    ./scripts/compose.sh up -d --wait --no-build --pull never
    ./scripts/compose.sh run --pull never --rm synthetic python scripts/synthetic-fixture.py verify
else
    echo 'Persistence restart check NOT RUN: set CONFIRM_RESTART_SYNTHETIC=yes explicitly.'
fi
echo 'Commands completed; retain actual output. ACME/cloud/VPS checks NOT covered.'
