from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps" / "backend"))

from app.db import SessionLocal, init_db  # noqa: E402
from app.services import ledger  # noqa: E402

TOOL_SCHEMAS = [
    {
        "name": "get_customer_ledger",
        "description": "Look up customer balance and recent transactions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "check_refund_eligibility",
        "description": "Deterministic refund eligibility decision. Never invent approvals.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "txn_id": {"type": "string"},
                "requested_amount_inr": {"type": "string"},
                "call_id": {"type": "string"},
                "auth_token": {"type": "string"},
            },
            "required": ["customer_id", "txn_id", "requested_amount_inr"],
        },
    },
    {
        "name": "execute_refund",
        "description": "Execute an eligible refund exactly once per effect_id. Requires OTP auth_token.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "txn_id": {"type": "string"},
                "amount_inr": {"type": "string"},
                "effect_id": {"type": "string"},
                "call_id": {"type": "string"},
                "auth_token": {"type": "string"},
            },
            "required": ["customer_id", "txn_id", "amount_inr", "effect_id", "auth_token"],
        },
    },
    {
        "name": "create_escalation_ticket",
        "description": "Create an escalation ticket for human queues.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "queue": {"type": "string"},
                "severity": {"type": "string"},
                "summary": {"type": "string"},
                "effect_id": {"type": "string"},
                "call_id": {"type": "string"},
            },
            "required": ["customer_id", "queue", "summary", "effect_id"],
        },
    },
    {
        "name": "schedule_callback",
        "description": "Schedule a callback window for the customer.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "window_start": {"type": "string"},
                "window_end": {"type": "string"},
                "effect_id": {"type": "string"},
                "call_id": {"type": "string"},
            },
            "required": ["customer_id", "window_start", "window_end", "effect_id"],
        },
    },
]


def _amount(value: str | float) -> float:
    return float(value)


def call_tool(name: str, arguments: dict) -> dict:
    init_db()
    chaos = arguments.pop("_chaos", None)
    if chaos:
        os.environ["CHAOS_FLAGS"] = chaos
    db = SessionLocal()
    try:
        if name == "get_customer_ledger":
            return ledger.get_ledger(db, arguments["customer_id"], int(arguments.get("limit", 5)))
        if name == "check_refund_eligibility":
            return ledger.eligibility(
                db,
                customer_id=arguments["customer_id"],
                txn_id=arguments["txn_id"],
                requested_amount_inr=_amount(arguments["requested_amount_inr"]),
                auth_token=arguments.get("auth_token"),
            )
        if name == "execute_refund":
            return ledger.execute_refund(
                db,
                customer_id=arguments["customer_id"],
                txn_id=arguments["txn_id"],
                amount_inr=_amount(arguments["amount_inr"]),
                effect_id=arguments["effect_id"],
                call_id=arguments.get("call_id"),
                auth_token=arguments.get("auth_token"),
            )
        if name == "create_escalation_ticket":
            return ledger.create_ticket(
                db,
                customer_id=arguments["customer_id"],
                queue=arguments["queue"],
                severity=arguments.get("severity", "medium"),
                summary=arguments["summary"],
                effect_id=arguments["effect_id"],
                call_id=arguments.get("call_id"),
            )
        if name == "schedule_callback":
            return ledger.schedule_callback(
                db,
                customer_id=arguments["customer_id"],
                window_start=arguments["window_start"],
                window_end=arguments["window_end"],
                effect_id=arguments["effect_id"],
                call_id=arguments.get("call_id"),
            )
        raise HTTPException(status_code=404, detail=f"Unknown tool {name}")
    except ledger.LedgerError as exc:
        status = 401 if exc.code == "auth_required" else 409 if exc.code == "policy_denied" else 503
        raise HTTPException(
            status_code=status,
            detail={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        ) from exc
    finally:
        db.close()
        if "_chaos" in arguments or chaos:
            os.environ.pop("CHAOS_FLAGS", None)
