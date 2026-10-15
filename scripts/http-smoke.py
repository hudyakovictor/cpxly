"""Through-Caddy test: real TLS verification, CSRF and session login, local mail."""
import http.client
import http.cookiejar
import json
import os
import ssl
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, HTTPSHandler, Request, build_opener

ca = Path(os.environ["TEST_CA_FILE"])
if not ca.stat().st_size:
    raise SystemExit("Export the local TEST CA first")
context = ssl.create_default_context(cafile=str(ca))
cookies = http.cookiejar.CookieJar()
opener = build_opener(HTTPSHandler(context=context), HTTPCookieProcessor(cookies))
base = "https://capexly.test"
with opener.open(Request(base + "/accounts/login/", headers={"X-Forwarded-Proto": "http"}), timeout=10) as response:
    if response.status != 200:
        raise SystemExit("HTTPS login form unavailable")
csrf = next((c.value for c in cookies if c.name == "csrftoken"), None)
if not csrf or not any(c.name == "csrftoken" and c.secure for c in cookies):
    raise SystemExit("Secure CSRF cookie missing")
password = Path(os.environ["SMOKE_PASSWORD_FILE"]).read_text().strip()
data = urlencode({"login": "infra-synthetic@example.test", "password": password, "csrfmiddlewaretoken": csrf}).encode()
request = Request(base + "/accounts/login/", data=data, headers={"Referer": base + "/accounts/login/", "Origin": base})
with opener.open(request, timeout=10) as response:
    response.read()
if not any(c.name == "sessionid" and c.secure for c in cookies):
    raise SystemExit("No secure authenticated session cookie")
with opener.open(base + "/users/profile/", timeout=10) as response:
    if "/accounts/login/" in response.url or response.status != 200:
        raise SystemExit("Authenticated profile request failed")
with opener.open("http://mailpit:8025/api/v1/messages", timeout=10) as response:
    mail = json.load(response)
if not any(m.get("Subject") == "Capexly synthetic infrastructure smoke" for m in mail.get("messages", [])):
    raise SystemExit("Synthetic email not present in local catcher")
# Verify static from the built Vite manifest, not frontend-dev.
manifest = json.loads(Path("/app/static/.vite/manifest.json").read_text())
asset = next(entry["file"] for entry in manifest.values() if entry.get("isEntry"))
with opener.open(base + "/static/" + asset, timeout=10) as response:
    if response.status != 200 or not response.read():
        raise SystemExit("Built static asset not served through Caddy")
# Application must redirect direct HTTP when no trusted scheme header is present.
conn = http.client.HTTPConnection("web", 8000, timeout=10)
conn.request("GET", "/healthz/", headers={"Host": "capexly.test"})
response = conn.getresponse()
if response.status not in (301, 302) or not response.getheader("Location", "").startswith("https://"):
    raise SystemExit("Missing HTTPS redirect")
response.read()
conn.close()
print("PASS verified test-CA HTTPS through Caddy; CSRF login/session; local email")
print("NOT a public ACME certificate or trusted production HTTPS test")
