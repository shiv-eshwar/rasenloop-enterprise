from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from rasen_client import FakeChaosTransport, RasenClient
from rasen_client.transport import LiveHttpTransport
from sqlalchemy.orm import Session

from app.models import AgentRelease, EvalRun
from app.settings import get_settings


def get_rasen_client() -> RasenClient:
    settings = get_settings()
    if settings.rasen_transport == "live" and settings.rasen_api_key:
        return RasenClient(LiveHttpTransport(settings.rasen_api_base, settings.rasen_api_key))
    return RasenClient(FakeChaosTransport())


def run_shadow_eval(
    db: Session,
    *,
    agent_id: str,
    candidate_version_id: str,
    previous_version_id: str | None,
) -> dict:
    """Run offline/fake eval suite and optionally rollback on blockers."""
    from rasenloop_eval.runner import run_suite

    settings = get_settings()
    eval_id = f"er_{uuid.uuid4().hex[:12]}"
    row = EvalRun(
        id=eval_id,
        candidate_version_id=candidate_version_id,
        status="running",
        report_json="{}",
    )
    db.add(row)
    db.commit()

    # Demo War Room "Run shadow eval" injects a blocker to exercise auto-rollback.
    inject = candidate_version_id.endswith("_bad") or "bad" in candidate_version_id
    report = run_suite(transport_mode=settings.rasen_transport, inject_blocker_failure=inject)
    blockers = [s for s in report["scenarios"] if s.get("severity") == "blocker" and not s["passed"]]
    passed = len(blockers) == 0
    rollback_receipt = None

    if not passed and previous_version_id and settings.control_plane_auto_eval:
        client = get_rasen_client()
        try:
            # Ensure fake agent graph exists for rollback demo
            if settings.rasen_transport != "live":
                created = client.create_agent(name="Demo", resource_key=f"demo-{agent_id}")
                aid = created.body["id"]
                draft = client.get_draft(aid)
                v1 = client.publish_agent(aid, if_match=draft.etag)
                draft2 = client.get_draft(aid)
                client.patch_draft(aid, {"prompt": "bad"}, if_match=draft2.etag)
                draft3 = client.get_draft(aid)
                v2 = client.publish_agent(aid, if_match=draft3.etag)
                rollback_receipt = client.rollback_agent(
                    aid,
                    version_id=v1["live_version_id"],
                    expected_live_version_id=v2["live_version_id"],
                )
            else:
                rollback_receipt = client.rollback_agent(
                    agent_id,
                    version_id=previous_version_id,
                    expected_live_version_id=candidate_version_id,
                )
            report["rollback"] = rollback_receipt
        except Exception as exc:  # noqa: BLE001 — capture for demo report
            report["rollback_error"] = str(exc)

    if passed:
        db.add(
            AgentRelease(
                version_id=candidate_version_id,
                agent_id=agent_id,
                source="eval_pass",
                notes="Shadow suite passed",
            )
        )

    row.status = "passed" if passed else "failed_rolled_back" if rollback_receipt else "failed"
    row.report_json = json.dumps(report)
    row.finished_at = datetime.now(UTC)
    db.commit()

    return {
        "eval_run_id": eval_id,
        "passed": passed,
        "blocker_scenarios": [b["id"] for b in blockers],
        "rollback": rollback_receipt,
        "report": report,
    }
