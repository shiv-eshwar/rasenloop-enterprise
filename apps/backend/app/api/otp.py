from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AuthSession

router = APIRouter(prefix="/otp", tags=["otp"])


class StartIn(BaseModel):
    customer_id: str
    call_id: str | None = None


class VerifyIn(BaseModel):
    session_id: str
    code: str


@router.post("/start")
def start_otp(body: StartIn, db: Session = Depends(get_db)) -> dict:
    code = "123456"  # demo fixed OTP; War Room / logs show it
    session_id = f"otp_{uuid.uuid4().hex[:12]}"
    auth_token = None
    row = AuthSession(
        id=session_id,
        customer_id=body.customer_id,
        call_id=body.call_id,
        otp_code=code,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        auth_token=auth_token,
    )
    db.add(row)
    db.commit()
    return {
        "session_id": session_id,
        "expires_at": row.expires_at.isoformat(),
        "demo_otp": code,
    }


@router.post("/verify")
def verify_otp(body: VerifyIn, db: Session = Depends(get_db)) -> dict:
    row = db.get(AuthSession, body.session_id)
    if not row:
        raise HTTPException(status_code=404, detail="OTP session not found")
    if row.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=410, detail="OTP expired")
    if body.code.strip() != row.otp_code:
        raise HTTPException(status_code=401, detail="Invalid OTP")
    row.verified_at = datetime.now(UTC)
    row.auth_token = f"auth_{uuid.uuid4().hex[:16]}"
    db.commit()
    return {"verified": True, "auth_token": row.auth_token}
