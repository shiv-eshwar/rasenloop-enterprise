from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Account, AuthSession, Callback, Effect, Refund, Ticket, Transaction
from app.policy import check_refund_eligibility
from app.services.crm import get_customer


class LedgerError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def _chaos_flags() -> set[str]:
    raw = os.environ.get("X_CHAOS", "") or os.environ.get("CHAOS_FLAGS", "")
    return {p.strip() for p in raw.split(",") if p.strip()}


def apply_chaos(tool_name: str) -> None:
    flags = _chaos_flags()
    if any(f.startswith("latency:") for f in flags):
        for f in flags:
            if f.startswith("latency:"):
                time.sleep(float(f.split(":", 1)[1]) / 1000.0)
    if "timeout" in flags and tool_name == "execute_refund":
        time.sleep(12)
        raise LedgerError("chaos_timeout", "Injected timeout")
    if "http:503" in flags and tool_name == "execute_refund":
        raise LedgerError("chaos_unavailable", "Injected 503", {"http_status": 503})


def get_ledger(db: Session, customer_id: str, limit: int = 5) -> dict:
    customer = get_customer(db, customer_id)
    if not customer:
        raise LedgerError("not_found", "Customer not found")
    account = customer.accounts[0] if customer.accounts else None
    if not account:
        raise LedgerError("not_found", "Account not found")
    txns = db.execute(
        select(Transaction)
        .where(Transaction.account_id == account.id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    ).scalars().all()
    return {
        "customer_id": customer_id,
        "available_balance_inr": f"{account.available_balance_inr:.2f}",
        "transactions": [
            {
                "txn_id": t.id,
                "amount_inr": f"{t.amount_inr:.2f}",
                "channel": t.channel,
                "status": t.status,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "merchant": t.merchant,
            }
            for t in txns
        ],
    }


def _auth_verified(db: Session, auth_token: str | None, customer_id: str) -> bool:
    if not auth_token:
        return False
    session = db.execute(
        select(AuthSession).where(
            AuthSession.auth_token == auth_token,
            AuthSession.customer_id == customer_id,
            AuthSession.verified_at.is_not(None),
        )
    ).scalar_one_or_none()
    return session is not None


def eligibility(
    db: Session,
    *,
    customer_id: str,
    txn_id: str,
    requested_amount_inr: float,
    auth_token: str | None = None,
) -> dict:
    customer = get_customer(db, customer_id)
    if not customer:
        raise LedgerError("not_found", "Customer not found")
    txn = db.get(Transaction, txn_id)
    if not txn:
        raise LedgerError("not_found", "Transaction not found")
    otp_verified = _auth_verified(db, auth_token, customer_id)
    decision = check_refund_eligibility(
        vip_tier=customer.vip_tier,
        fraud_flag=customer.fraud_flag,
        txn_status=txn.status,
        txn_amount_inr=txn.amount_inr,
        requested_amount_inr=requested_amount_inr,
        otp_verified=otp_verified,
    )
    payload = asdict(decision)
    payload["max_amount_inr"] = f"{decision.max_amount_inr:.2f}"
    return payload


def execute_refund(
    db: Session,
    *,
    customer_id: str,
    txn_id: str,
    amount_inr: float,
    effect_id: str,
    call_id: str | None = None,
    auth_token: str | None = None,
    partial_write: bool = False,
) -> dict:
    existing = db.execute(select(Refund).where(Refund.effect_id == effect_id)).scalar_one_or_none()
    if existing:
        return {
            "status": existing.status,
            "refund_id": existing.id,
            "effect_id": effect_id,
            "amount_inr": f"{existing.amount_inr:.2f}",
            "idempotent_replay": True,
        }

    if not _auth_verified(db, auth_token, customer_id):
        raise LedgerError("auth_required", "OTP verification required before refund")

    decision_raw = eligibility(
        db,
        customer_id=customer_id,
        txn_id=txn_id,
        requested_amount_inr=amount_inr,
        auth_token=auth_token,
    )
    if decision_raw["decision"] != "allow":
        raise LedgerError("policy_denied", "Refund denied by policy", decision_raw)

    effect = Effect(
        effect_id=effect_id,
        tool_name="execute_refund",
        call_id=call_id,
        status="pending",
        request_hash=f"{customer_id}:{txn_id}:{amount_inr}",
    )
    db.add(effect)
    db.flush()

    flags = _chaos_flags()
    try:
        if "partial_write" in flags or partial_write:
            # Simulate ambiguous failure after intent recorded.
            effect.status = "indeterminate"
            db.commit()
            raise LedgerError("chaos_timeout", "Partial write then failure")

        apply_chaos("execute_refund")

        refund = Refund(
            id=f"ref_{uuid.uuid4().hex[:12]}",
            effect_id=effect_id,
            transaction_id=txn_id,
            customer_id=customer_id,
            amount_inr=amount_inr,
            status="executed",
            policy_code=decision_raw["policy_code"],
        )
        account = db.execute(
            select(Account).where(Account.customer_id == customer_id)
        ).scalar_one()
        account.available_balance_inr += amount_inr
        effect.status = "executed"
        effect.result_json = json.dumps({"refund_id": refund.id})
        db.add(refund)
        db.commit()
        return {
            "status": "executed",
            "refund_id": refund.id,
            "effect_id": effect_id,
            "amount_inr": f"{amount_inr:.2f}",
        }
    except LedgerError as exc:
        if effect.status != "indeterminate":
            effect.status = "indeterminate" if exc.code in {"chaos_timeout", "chaos_unavailable"} else "failed"
            effect.result_json = json.dumps({"error": exc.code})
            db.commit()
        raise


def create_ticket(
    db: Session,
    *,
    customer_id: str,
    queue: str,
    severity: str,
    summary: str,
    effect_id: str,
    call_id: str | None = None,
) -> dict:
    existing = db.execute(select(Ticket).where(Ticket.effect_id == effect_id)).scalar_one_or_none()
    if existing:
        return {"ticket_id": existing.id, "status": existing.status, "idempotent_replay": True}
    ticket = Ticket(
        id=f"tkt_{uuid.uuid4().hex[:12]}",
        effect_id=effect_id,
        customer_id=customer_id,
        queue=queue,
        severity=severity,
        summary=summary,
        call_id=call_id,
        status="open",
    )
    db.add(
        Effect(
            effect_id=effect_id,
            tool_name="create_escalation_ticket",
            call_id=call_id,
            status="executed",
            result_json=json.dumps({"ticket_id": ticket.id}),
        )
    )
    db.add(ticket)
    db.commit()
    return {"ticket_id": ticket.id, "status": "open"}


def schedule_callback(
    db: Session,
    *,
    customer_id: str,
    window_start: str,
    window_end: str,
    effect_id: str,
    call_id: str | None = None,
) -> dict:
    existing = db.execute(select(Callback).where(Callback.effect_id == effect_id)).scalar_one_or_none()
    if existing:
        return {"callback_id": existing.id, "status": existing.status, "idempotent_replay": True}
    cb = Callback(
        id=f"cb_{uuid.uuid4().hex[:12]}",
        effect_id=effect_id,
        customer_id=customer_id,
        window_start=window_start,
        window_end=window_end,
        call_id=call_id,
        status="scheduled",
    )
    db.add(
        Effect(
            effect_id=effect_id,
            tool_name="schedule_callback",
            call_id=call_id,
            status="executed",
            result_json=json.dumps({"callback_id": cb.id}),
        )
    )
    db.add(cb)
    db.commit()
    return {"callback_id": cb.id, "status": "scheduled"}
