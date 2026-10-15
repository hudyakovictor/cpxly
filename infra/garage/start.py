import os
from pathlib import Path

# Read mounts at startup. Never bake credentials into ARG/ENV or log values.
access = Path("/run/secrets/s3_access_key").read_text().strip()
secret = Path("/run/secrets/s3_secret_key").read_text().strip()
if not access.startswith("GK") or len(access) != 34:
    raise SystemExit("Garage dev access key must be GK followed by 32 hex digits")
try:
    bytes.fromhex(access[2:])
except ValueError:
    raise SystemExit("Garage dev access key has invalid format") from None
if len(secret) != 64:
    raise SystemExit("Garage dev secret must contain 64 hex digits")
try:
    bytes.fromhex(secret)
except ValueError:
    raise SystemExit("Garage dev secret has invalid format") from None
os.environ["GARAGE_DEFAULT_ACCESS_KEY"] = access
os.environ["GARAGE_DEFAULT_SECRET_KEY"] = secret
os.environ["GARAGE_DEFAULT_BUCKET"] = os.environ["S3_BUCKET"]
os.execv("/garage", ["/garage", "server", "--single-node", "--default-bucket"])
