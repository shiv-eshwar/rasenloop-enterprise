import time

from app.services.webhooks_crypto import sign_webhook, verify_webhook


def test_verify_webhook_accepts_valid_signature():
    secret = "whsec_" + __import__("base64").b64encode(__import__("os").urandom(32)).decode()
    body = b'{"type":"webhook.test"}'
    webhook_id = "wevt_01test"
    timestamp = str(int(time.time()))
    signature = sign_webhook(secret, webhook_id, timestamp, body)
    ok = verify_webhook(
        secret,
        {
            "webhook-id": webhook_id,
            "webhook-timestamp": timestamp,
            "webhook-signature": signature,
        },
        body,
    )
    assert ok is True


def test_verify_webhook_rejects_bad_signature():
    secret = "whsec_" + __import__("base64").b64encode(b"0123456789abcdef0123456789abcdef").decode()
    ok = verify_webhook(
        secret,
        {
            "webhook-id": "wevt_x",
            "webhook-timestamp": str(int(time.time())),
            "webhook-signature": "v1,AAAA",
        },
        b"{}",
    )
    assert ok is False
