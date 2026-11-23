from rasen_client import FakeChaosTransport, RasenClient


def test_create_agent_sends_idempotency_key_and_persists_it():
    transport = FakeChaosTransport()
    client = RasenClient(transport)

    key = "intent-create-agent-001"
    response = client.create_agent(
        name="BharatPay Support",
        resource_key="bharatpay-support-line",
        initial_draft={
            "prompt": "You are BharatPay support.",
            "settings": {"language": "hinglish", "first_message": "Namaste"},
        },
        idempotency_key=key,
    )

    assert response.status_code == 201
    assert client.get_persisted_idempotency_key("create_agent") == key
    assert transport.requests[0].headers["Idempotency-Key"] == key
    assert response.body["id"].startswith("agent_")


def test_identical_create_agent_replays_without_second_agent():
    transport = FakeChaosTransport()
    client = RasenClient(transport)
    key = "intent-create-agent-002"

    first = client.create_agent(
        name="Support",
        resource_key="support-line",
        idempotency_key=key,
    )
    second = client.create_agent(
        name="Support",
        resource_key="support-line",
        idempotency_key=key,
    )

    assert first.body["id"] == second.body["id"]
    assert second.idempotent_replayed is True
    assert len(transport._agents) == 1


def test_patch_draft_requires_if_match_and_updates_etag():
    transport = FakeChaosTransport()
    client = RasenClient(transport)
    created = client.create_agent(name="Support", resource_key="support-line")
    agent_id = created.body["id"]

    draft = client.get_draft(agent_id)
    etag = draft.etag
    assert etag

    updated = client.patch_draft(
        agent_id,
        {"prompt": "Updated prompt"},
        if_match=etag,
        idempotency_key="intent-patch-001",
    )
    assert updated.body["prompt"] == "Updated prompt"
    assert updated.etag != etag
    assert transport.requests[-1].headers["If-Match"] == etag


def test_publish_and_rollback_roundtrip():
    transport = FakeChaosTransport()
    client = RasenClient(transport)
    created = client.create_agent(name="Support", resource_key="support-line")
    agent_id = created.body["id"]
    draft = client.get_draft(agent_id)
    v1 = client.publish_agent(agent_id, if_match=draft.etag)

    draft2 = client.get_draft(agent_id)
    client.patch_draft(
        agent_id,
        {"prompt": "Bad prompt that invents refunds"},
        if_match=draft2.etag,
    )
    draft3 = client.get_draft(agent_id)
    v2 = client.publish_agent(agent_id, if_match=draft3.etag)

    receipt = client.rollback_agent(
        agent_id,
        version_id=v1["live_version_id"],
        expected_live_version_id=v2["live_version_id"],
    )
    assert receipt["to_version_id"] == v1["live_version_id"]
    assert client.get_agent(agent_id)["live_version_id"] == v1["live_version_id"]


def test_revoke_secret_version_for_kill_switch():
    transport = FakeChaosTransport()
    client = RasenClient(transport)
    secret = client.create_secret(
        purpose="mcp_server",
        name="mcp-refund",
        resource_key="mcp-refund-prod",
        value="secret-value",
    )
    revoked = client.revoke_secret_version(secret["id"], 1, reason="compromised")
    assert revoked["state"] == "revoked"
    assert revoked["version"] == 1
