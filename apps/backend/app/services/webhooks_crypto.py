from __future__ import annotations

import base64
import hashlib
import hmac
import time


def verify_webhook(
    secret: str,
    headers: dict[str, str],
    body: bytes,
    *,
    tolerance_seconds: int = 300,
) -> bool:
    webhook_id = headers.get("webhook-id", "")
    timestamp = headers.get("webhook-timestamp", "")
    signatures = headers.get("webhook-signature", "")
    if not webhook_id or not timestamp.isdigit() or not signatures:
        return False
    if abs(time.time() - int(timestamp)) > tolerance_seconds:
        return False
    key = base64.b64decode(secret.removeprefix("whsec_"))
    signed = f"{webhook_id}.{timestamp}.".encode() + body
    expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    for value in signatures.split(" "):
        version, _, signature = value.partition(",")
        if version == "v1" and hmac.compare_digest(signature, expected):
            return True
    return False


def sign_webhook(secret: str, webhook_id: str, timestamp: str, body: bytes) -> str:
    key = base64.b64decode(secret.removeprefix("whsec_"))
    digest = hmac.new(key, f"{webhook_id}.{timestamp}.".encode() + body, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode()
