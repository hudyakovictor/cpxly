"""Read-only verified TLS expiry check; never disables certificate validation."""
import os
import socket
import ssl
from datetime import datetime, timezone

host = os.environ["TLS_CHECK_HOST"]
port = int(os.environ.get("TLS_CHECK_PORT", "443"))
context = ssl.create_default_context(cafile=os.environ.get("TEST_CA_FILE"))
with socket.create_connection((host, port), timeout=10) as raw:
    with context.wrap_socket(raw, server_hostname=host) as connection:
        cert = connection.getpeercert()
expiry = ssl.cert_time_to_seconds(cert["notAfter"])
remaining = (expiry - datetime.now(timezone.utc).timestamp()) / 86400
print("Verified TLS certificate expires:", cert["notAfter"])
print("Days remaining:", round(remaining, 1))
if remaining < 14:
    raise SystemExit("Certificate expiry is within the 14-day alert window")
