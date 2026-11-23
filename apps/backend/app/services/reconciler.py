from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Effect, Refund


def reconcile_effect(db: Session, effect_id: str) -> dict:
    effect = db.get(Effect, effect_id)
    if not effect:
        return {"effect_id": effect_id, "status": "missing"}
    if effect.status in {"executed", "failed", "denied"}:
        return {"effect_id": effect_id, "status": effect.status, "noop": True}

    refund = db.execute(select(Refund).where(Refund.effect_id == effect_id)).scalar_one_or_none()
    if refund:
        effect.status = "executed"
        effect.reconciled_at = datetime.now(UTC)
        effect.result_json = json.dumps({"refund_id": refund.id, "reconciled": True})
        db.commit()
        return {"effect_id": effect_id, "status": "executed", "refund_id": refund.id}

    effect.status = "failed"
    effect.reconciled_at = datetime.now(UTC)
    effect.result_json = json.dumps({"reconciled": True, "ledger_row": False})
    db.commit()
    return {"effect_id": effect_id, "status": "failed", "safe_to_retry_with_new_effect_id": True}


def reconcile_pending(db: Session) -> list[dict]:
    effects = db.execute(
        select(Effect).where(Effect.status.in_(["indeterminate", "pending"]))
    ).scalars().all()
    return [reconcile_effect(db, e.effect_id) for e in effects]
