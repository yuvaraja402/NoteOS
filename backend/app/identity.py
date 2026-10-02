"""Anonymous device identity. IP addresses only contribute to abuse controls."""

import hashlib
import hmac
from uuid import UUID, uuid4

COOKIE_NAME = "noteos_device"
COOKIE_MAX_AGE = 365 * 24 * 60 * 60


def digest(secret: str, purpose: str, value: str) -> str:
    return hmac.new(secret.encode(), f"{purpose}:{value}".encode(), hashlib.sha256).hexdigest()


def device_identity(cookie: str | None, secret: str) -> tuple[str, str, bool]:
    if cookie:
        try:
            device_id, signature = cookie.split(".", 1)
            UUID(device_id)
            if hmac.compare_digest(signature, digest(secret, "cookie", device_id)):
                return digest(secret, "workspace", device_id), cookie, False
        except (ValueError, AttributeError):
            pass
    device_id = str(uuid4())
    token = f"{device_id}.{digest(secret, 'cookie', device_id)}"
    return digest(secret, "workspace", device_id), token, True
