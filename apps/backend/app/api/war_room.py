from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CallMirror, EvalRun, ProductionSignal
from app.services.control_plane import get_rasen_client, run_shadow_eval
from app.services.reconciler import reconcile_pending
from app.services.signals import list_signals
from app.settings import get_settings

router = APIRouter(prefix="/war-room", tags=["war-room"])


def _auth(authorization: str | None = Header(default=None)) -> None:
    settings = get_settings()
    expected = settings.war_room_password
    if authorization == f"Bearer {expected}" or authorization == expected:
        return
    # Allow open local demo with password header alternative
    raise HTTPException(status_code=401, detail="Unauthorized — use Bearer <WAR_ROOM_PASSWORD>")


class KillSwitchIn(BaseModel):
    reason: str = "compromised"
    secret_id: str | None = None
    secret_version: int | None = None


class EvalRunIn(BaseModel):
    agent_id: str
    candidate_version_id: str
    previous_version_id: str | None = None


@router.get("/calls")
def list_calls(
    active: int = 1,
    db: Session = Depends(get_db),
    _: None = Depends(_auth),
) -> dict[str, Any]:
    stmt = select(CallMirror).order_by(CallMirror.updated_at.desc()).limit(50)
    if active:
        stmt = select(CallMirror).where(CallMirror.active.is_(True)).order_by(CallMirror.updated_at.desc())
    items = db.execute(stmt).scalars().all()
    return {
        "items": [
            {
                "call_id": c.call_id,
                "agent_id": c.agent_id,
                "state": c.state,
                "end_reason": c.end_reason,
                "active": c.active,
                "published_version_id": c.published_version_id,
            }
            for c in items
        ]
    }


@router.get("/calls/{call_id}")
def get_call(call_id: str, db: Session = Depends(get_db), _: None = Depends(_auth)) -> dict:
    call = db.get(CallMirror, call_id)
    if not call:
        # Synthetic active call for demo when none mirrored yet
        return {
            "call_id": call_id,
            "state": "unknown",
            "brief": {
                "identity": "Unknown caller",
                "auth_level": "none",
                "tools_run": [],
                "unresolved_blocker": "No mirrored call yet",
            },
        }
    return {
        "call_id": call.call_id,
        "state": call.state,
        "end_reason": call.end_reason,
        "transcript_text": call.transcript_text,
        "metadata": json.loads(call.metadata_json or "{}"),
        "brief": {
            "identity": json.loads(call.metadata_json or "{}").get("customer_name", "Caller"),
            "auth_level": "otp_verified_or_unknown",
            "tools_run": [],
            "unresolved_blocker": None if call.state else "in_progress",
        },
        "frustration_score": _frustration(call.transcript_text),
    }


def _frustration(text: str) -> int:
    lower = (text or "").lower()
    score = 0
    for word in ["angry", "fraud", "refund now", "manager", "useless", "scam", "gussa"]:
        if word in lower:
            score += 20
    return min(score, 100)


@router.get("/calls/{call_id}/transcript/live")
def live_transcript_proxy(call_id: str, _: None = Depends(_auth)) -> dict:
    """MVP: return mirrored transcript; live SSE proxy can be added when RASEN live call exists."""
    return {
        "call_id": call_id,
        "mode": "mirror_poll",
        "note": "Connect RASEN live SSE in production; demo uses mirrored/analyzed text.",
    }


@router.post("/kill-switch")
def kill_switch(body: KillSwitchIn, db: Session = Depends(get_db), _: None = Depends(_auth)) -> dict:
    settings = get_settings()
    secret_id = body.secret_id or settings.refund_secret_id or "sec_demo"
    version = body.secret_version or settings.refund_secret_version
    client = get_rasen_client()

    # Ensure a secret exists in fake transport
    if settings.rasen_transport != "live":
        try:
            created = client.create_secret(
                purpose="mcp_server",
                name="mcp-refund",
                resource_key="mcp-refund-prod",
                value="demo",
            )
            secret_id = created["id"]
            version = 1
        except Exception:
            pass

    revoked = client.revoke_secret_version(secret_id, version, reason=body.reason)
    from shared.signals import SignalSeverity, SignalType

    db.add(
        ProductionSignal(
            call_id="system",
            signal_type=SignalType.KILL_SWITCH_ENGAGED.value,
            severity=SignalSeverity.CRITICAL.value,
            evidence_json=json.dumps(revoked),
        )
    )
    db.commit()
    return {
        "revoked_version": revoked.get("version", version),
        "secret_id": revoked.get("secret_id", secret_id),
        "rasen_request_id": None,
        "result": revoked,
    }


@router.get("/signals")
def signals(limit: int = 50, db: Session = Depends(get_db), _: None = Depends(_auth)) -> dict:
    rows = list_signals(db, limit=limit)
    return {
        "items": [
            {
                "id": r.id,
                "call_id": r.call_id,
                "signal_type": r.signal_type,
                "severity": r.severity,
                "evidence": json.loads(r.evidence_json or "{}"),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.get("/evals/latest")
def latest_eval(db: Session = Depends(get_db), _: None = Depends(_auth)) -> dict:
    row = db.execute(select(EvalRun).order_by(EvalRun.started_at.desc()).limit(1)).scalar_one_or_none()
    if not row:
        return {"eval": None}
    return {
        "eval": {
            "id": row.id,
            "candidate_version_id": row.candidate_version_id,
            "status": row.status,
            "report": json.loads(row.report_json or "{}"),
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        }
    }


@router.post("/evals/run")
def trigger_eval(body: EvalRunIn, db: Session = Depends(get_db), _: None = Depends(_auth)) -> dict:
    return run_shadow_eval(
        db,
        agent_id=body.agent_id,
        candidate_version_id=body.candidate_version_id,
        previous_version_id=body.previous_version_id,
    )


@router.post("/reconcile")
def reconcile(db: Session = Depends(get_db), _: None = Depends(_auth)) -> dict:
    return {"results": reconcile_pending(db)}


@router.post("/demo/active-call")
def create_demo_active_call(db: Session = Depends(get_db), _: None = Depends(_auth)) -> dict:
    call_id = "call_demo_active"
    mirror = db.get(CallMirror, call_id) or CallMirror(call_id=call_id)
    mirror.active = True
    mirror.state = "active"
    mirror.agent_id = "agent_demo"
    mirror.transcript_text = "agent: Namaste Priya\ncustomer: Mera UPI refund chahiye"
    mirror.metadata_json = json.dumps({"customer_name": "Priya Sharma", "vip_tier": "vip"})
    db.add(mirror)
    db.commit()
    return {"call_id": call_id, "active": True}
