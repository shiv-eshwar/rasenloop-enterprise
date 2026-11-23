from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Account, Customer


def _customer_options():
    return (
        selectinload(Customer.accounts).selectinload(Account.transactions),
        selectinload(Customer.incidents),
    )


def get_customer_by_phone(db: Session, phone: str) -> Customer | None:
    stmt = select(Customer).where(Customer.phone_e164 == phone).options(*_customer_options())
    return db.execute(stmt).scalar_one_or_none()


def get_customer(db: Session, customer_id: str) -> Customer | None:
    stmt = select(Customer).where(Customer.id == customer_id).options(*_customer_options())
    return db.execute(stmt).scalar_one_or_none()


def customer_360_payload(customer: Customer) -> dict:
    recent_failed = []
    for account in customer.accounts:
        for txn in sorted(account.transactions, key=lambda t: t.created_at or 0, reverse=True):
            if txn.status in {"failed", "disputed_eligible"}:
                recent_failed.append(
                    {
                        "txn_id": txn.id,
                        "amount_inr": f"{txn.amount_inr:.2f}",
                        "channel": txn.channel,
                        "status": txn.status,
                        "merchant": txn.merchant,
                    }
                )
            if len(recent_failed) >= 5:
                break
    return {
        "name": customer.name,
        "customer_id": customer.id,
        "vip_tier": customer.vip_tier,
        "fraud_flag": customer.fraud_flag,
        "language_preference": customer.language_preference,
        "open_incidents": [
            {"id": i.id, "summary": i.summary}
            for i in customer.incidents
            if i.status == "open"
        ],
        "recent_failed_transactions": recent_failed,
        "auth_hint": "otp_required_for_refunds",
    }
