"""Effect lifecycle helpers — thin wrappers around ledger + reconciler."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.reconciler import reconcile_effect, reconcile_pending


def reconcile(db: Session, effect_id: str) -> dict:
    return reconcile_effect(db, effect_id)


def reconcile_all(db: Session) -> list[dict]:
    return reconcile_pending(db)
