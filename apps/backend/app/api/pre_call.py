from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.crm import customer_360_payload, get_customer_by_phone
from app.settings import get_settings

router = APIRouter(tags=["pre-call"])


class LookupCallerBody(BaseModel):
    phone: str | None = None
    system__caller_id: str | None = Field(default=None, alias="system__caller_id")

    model_config = {"populate_by_name": True}


def _lookup(phone: str, db: Session) -> dict:
    settings = get_settings()
    started = time.perf_counter()
    customer = get_customer_by_phone(db, phone)
    elapsed_ms = (time.perf_counter() - started) * 1000
    if not customer:
        return {
            "name": None,
            "customer_id": None,
            "vip_tier": "unknown",
            "fraud_flag": False,
            "open_incidents": [],
            "recent_failed_transactions": [],
            "auth_hint": "otp_required_for_refunds",
            "pre_call_miss": True,
            "latency_ms": round(elapsed_ms, 2),
        }

    payload = customer_360_payload(customer)
    payload["latency_ms"] = round(elapsed_ms, 2)
    if elapsed_ms > settings.pre_call_deadline_ms:
        payload["pre_call_slow"] = True
    return payload


def _require_key(x_api_key: str | None) -> None:
    settings = get_settings()
    if settings.rasen_transport == "live" and not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-Api-Key")


@router.get("/pre-call/lookup_caller")
def lookup_caller_get(
    phone: str = Query(..., description="E.164 from system__caller_id"),
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
    db: Session = Depends(get_db),
) -> dict:
    _require_key(x_api_key)
    return _lookup(phone, db)


@router.post("/pre-call/lookup_caller")
async def lookup_caller_post(
    request: Request,
    body: LookupCallerBody | None = None,
    phone: str | None = Query(default=None),
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
    db: Session = Depends(get_db),
) -> dict:
    _require_key(x_api_key)
    resolved = phone
    if body:
        resolved = resolved or body.phone or body.system__caller_id
    if not resolved:
        try:
            raw = await request.json()
            resolved = raw.get("phone") or raw.get("system__caller_id")
        except Exception:  # noqa: BLE001
            resolved = None
    if not resolved:
        raise HTTPException(status_code=422, detail="phone required")
    return _lookup(resolved, db)
