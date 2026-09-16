"""Generate local server configuration; print only the non-secret SHA-256 digest."""

import hashlib
import secrets
from pathlib import Path

from dotenv import dotenv_values, set_key

backend = Path(__file__).resolve().parents[1]
environment = backend / ".env"
values = dotenv_values(environment)
secret = values.get("REPORT_PROCESSING_KEY") or secrets.token_urlsafe(48)
if len(secret) < 40:
    raise RuntimeError("Existing processing secret is too short")
set_key(str(environment), "REPORT_PROCESSING_KEY", secret)
print(hashlib.sha256(secret.encode()).hexdigest())
