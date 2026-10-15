#!/usr/bin/env python3
"""Explicit synthetic provisioning; never reads or writes production secrets."""
import argparse
import os
import secrets
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--environment", choices=["dev", "prod-test", "ci", "restore-test"], default="dev")
args = parser.parse_args()
root = Path("secrets") / args.environment
root.mkdir(parents=True, exist_ok=True)
os.chmod(root, 0o700)
names = (
    "db_bootstrap_password", "db_migrator_password", "db_runtime_password",
    "django_secret_key", "s3_access_key", "s3_secret_key", "smtp_password",
    "garage_rpc_secret", "smoke_user_password",
)
for name in names:
    p = root / name
    if p.exists():
        if p.is_symlink() or (p.stat().st_mode & 0o777) != 0o444:
            raise SystemExit(f"Existing secret {name} needs explicit file-permission review; unchanged")
        continue
    value = secrets.token_urlsafe(40)
    if name == "s3_access_key":
        value = "GK" + secrets.token_hex(16)
    elif name in ("s3_secret_key", "garage_rpc_secret"):
        value = secrets.token_hex(32)
    # Compose file-backed secrets ignore uid/gid remapping. Files are readable
    # inside only the containers mounting them; HOST parent directory is 0700.
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(fd, "w") as f:
        f.write(value + "\n")
        os.fchmod(f.fileno(), 0o444)
# Placeholder public CA mount; must be explicitly populated after Caddy startup.
p = root / "test_ca.crt"
if not p.exists():
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    os.close(fd)
print("Synthetic files prepared; no values printed; existing files unchanged.")
