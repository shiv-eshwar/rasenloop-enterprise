from app.db import Base, SessionLocal, engine, init_db
from app.services.control_plane import get_rasen_client, run_shadow_eval
from rasen_client import FakeChaosTransport


def test_kill_switch_revokes_secret_on_fake():
    client = get_rasen_client()
    assert isinstance(client.transport, FakeChaosTransport)
    secret = client.create_secret(
        purpose="mcp_server",
        name="mcp-refund",
        resource_key="mcp-refund-kill",
        value="token",
    )
    revoked = client.revoke_secret_version(secret["id"], 1, reason="compromised")
    assert revoked["state"] == "revoked"
    assert revoked["version"] == 1


def test_bad_candidate_triggers_rollback():
    init_db()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    result = run_shadow_eval(
        db,
        agent_id="agent_demo",
        candidate_version_id="pub_candidate_bad",
        previous_version_id="pub_previous",
    )
    assert result["passed"] is False
    assert result["rollback"] is not None
    assert "to_version_id" in result["rollback"]
    db.close()


def test_good_candidate_passes_without_rollback():
    init_db()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    result = run_shadow_eval(
        db,
        agent_id="agent_demo",
        candidate_version_id="pub_candidate_good",
        previous_version_id="pub_previous",
    )
    assert result["passed"] is True
    assert result["rollback"] is None
    db.close()
