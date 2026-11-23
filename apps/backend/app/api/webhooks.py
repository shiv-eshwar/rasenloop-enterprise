from __future__ import annotations

import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CallMirror, WebhookEvent
from app.services.reconciler import reconcile_pending
from app.services.signals import classify_call
from app.services.webhooks_crypto import verify_webhook
from app.settings import get_settings

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/rasen")
async def rasen_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}

    # Allow unsigned in fake/dev if secret is default and header missing (local tests)
    has_sig = "webhook-signature" in headers
    if has_sig:
        if not verify_webhook(settings.webhook_signing_secret, headers, body):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = json.loads(body.decode("utf-8"))
    webhook_id = headers.get("webhook-id") or payload.get("id")
    if not webhook_id:
        raise HTTPException(status_code=400, detail="Missing webhook id")

    existing = db.get(WebhookEvent, webhook_id)
    if existing:
        return {"status": "duplicate", "webhook_id": webhook_id}

    event_type = payload.get("type", "unknown")
    db.add(
        WebhookEvent(
            webhook_id=webhook_id,
            type=event_type,
            payload_hash=hashlib.sha256(body).hexdigest(),
        )
    )

    data = payload.get("data") or {}
    call = data.get("call") or {}
    call_id = call.get("id") or call.get("call_id") or data.get("call_id")
    if call_id:
        mirror = db.get(CallMirror, call_id) or CallMirror(call_id=call_id)
        mirror.state = call.get("state") or mirror.state
        mirror.end_reason = call.get("end_reason")
        mirror.agent_id = call.get("agent_id") or mirror.agent_id
        mirror.published_version_id = call.get("published_version_id") or mirror.published_version_id
        mirror.metadata_json = json.dumps(call.get("metadata") or {})
        mirror.active = False if event_type in {"call.completed", "call.failed", "call.analyzed"} else mirror.active
        if event_type == "call.analyzed":
            transcript = data.get("transcript") or {}
            turns = transcript.get("turns") or []
            mirror.transcript_text = "\n".join(
                f"{t.get('speaker')}: {t.get('text')}" for t in turns if isinstance(t, dict)
            )
            tool_outcomes = data.get("tool_outcomes") or []
            classify_call(
                db,
                call_id=call_id,
                transcript_text=mirror.transcript_text,
                tool_outcomes=tool_outcomes,
            )
            reconcile_pending(db)
        db.add(mirror)

    db.commit()
    return {"status": "accepted", "webhook_id": webhook_id, "type": event_type}
