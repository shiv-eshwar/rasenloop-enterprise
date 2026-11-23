from __future__ import annotations

import json
import re

from shared.signals import SignalSeverity, SignalType
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProductionSignal

SUCCESS_PHRASES = [
    "refund ho gaya",
    "refunded successfully",
    "money has been refunded",
    "refund is done",
    "refund complete",
]


def classify_call(
    db: Session,
    *,
    call_id: str,
    transcript_text: str,
    tool_outcomes: list[dict],
) -> list[ProductionSignal]:
    created: list[ProductionSignal] = []

    def add(signal_type: SignalType, severity: SignalSeverity, evidence: dict) -> None:
        row = ProductionSignal(
            call_id=call_id,
            signal_type=signal_type.value,
            severity=severity.value,
            evidence_json=json.dumps(evidence),
        )
        db.add(row)
        created.append(row)

    lower = (transcript_text or "").lower()
    refund_executed = any(
        (o.get("tool_name") == "execute_refund" and o.get("state") == "succeeded")
        for o in tool_outcomes
    )
    if any(p in lower for p in SUCCESS_PHRASES) and not refund_executed:
        add(
            SignalType.GROUNDING_UNVERIFIED_PROMISE,
            SignalSeverity.BLOCKER,
            {"phrases": [p for p in SUCCESS_PHRASES if p in lower]},
        )

    for outcome in tool_outcomes:
        latency = outcome.get("latency_ms")
        if isinstance(latency, (int, float)) and latency > 2000:
            add(
                SignalType.TOOL_LATENCY_SPIKE,
                SignalSeverity.MED,
                {"tool": outcome.get("tool_name"), "latency_ms": latency},
            )
        if outcome.get("tool_name") == "execute_refund" and outcome.get("state") == "indeterminate":
            add(
                SignalType.INDETERMINATE_REFUND,
                SignalSeverity.HIGH,
                {"outcome": outcome},
            )

    # Simple escalation loop: repeated same question markers
    if len(re.findall(r"could you (please )?repeat|dobara|again please", lower)) >= 3:
        add(SignalType.ESCALATION_LOOP, SignalSeverity.MED, {"pattern": "repeat_requests"})

    db.commit()
    return created


def list_signals(db: Session, limit: int = 50) -> list[ProductionSignal]:
    return list(
        db.execute(
            select(ProductionSignal).order_by(ProductionSignal.id.desc()).limit(limit)
        ).scalars()
    )
