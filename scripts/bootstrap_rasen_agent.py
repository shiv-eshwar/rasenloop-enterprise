#!/usr/bin/env python3
"""Bootstrap a Rasen agent (live) or print fake bootstrap plan."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "rasen-client"))

from rasen_client import FakeChaosTransport, RasenClient  # noqa: E402
from rasen_client.transport import LiveHttpTransport  # noqa: E402


def main() -> None:
    transport_mode = os.environ.get("RASEN_TRANSPORT", "fake")
    base = os.environ.get("RASEN_API_BASE", "https://api.rasen.ai/v1")
    key = os.environ.get("RASEN_API_KEY", "")
    public = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
    mcp_url = os.environ.get("MCP_PUBLIC_URL", "http://localhost:8001/mcp")

    if transport_mode == "live" and key:
        client = RasenClient(LiveHttpTransport(base, key))
    else:
        client = RasenClient(FakeChaosTransport())
        print("Using FakeChaosTransport (set RASEN_TRANSPORT=live + RASEN_API_KEY for real publish)")

    ctx = client.get_context()
    print("context:", json.dumps(ctx, indent=2)[:500])

    voices = client.list_voices()
    voice_id = voices["items"][0]["id"]

    created = client.create_agent(
        name="BharatPay Support",
        resource_key="bharatpay-support-line",
        description="Pan-India fintech inbound support",
        initial_draft={
            "prompt": (
                "You are BharatPay support. Speak Hinglish naturally. "
                "Never invent refunds. Use tools for ledger, eligibility, refunds, tickets. "
                "Require OTP before execute_refund. Transfer Fraud Desk on fraud_flag."
            ),
            "voice": {"voice_id": voice_id},
            "settings": {
                "language": "hinglish",
                "call_direction": "inbound",
                "first_message": (
                    "Namaste {{lookup_caller.name|there}}, BharatPay support mein aapka swagat hai."
                ),
                "dtmf_enabled": True,
            },
            "default_tools": {"end_call": {"enabled": True}},
        },
    )
    agent_id = created.body["id"]
    print("agent_id:", agent_id)

    secret = client.create_secret(
        purpose="webhook_tool",
        name="precall-api-key",
        resource_key="precall-prod",
        value=os.environ.get("PRECALL_API_KEY", "demo-precall-key"),
    )
    mcp_secret = client.create_secret(
        purpose="mcp_server",
        name="mcp-refund",
        resource_key="mcp-refund-prod",
        value=os.environ.get("MCP_AUTH_TOKEN", "mcp-dev-token"),
    )

    draft = client.get_draft(agent_id)
    tool = client.create_agent_tool(
        agent_id,
        {
            "name": "lookup_caller",
            "description": "Lookup caller CRM while ringing",
            "kind": "webhook",
            "timing": "pre_call",
            "side_effect": "none",
            "retry_posture": "none",
            "definition": {
                "url": f"{public}/pre-call/lookup_caller",
                "method": "GET",
                "parameters": [
                    {
                        "name": "phone",
                        "location": "query",
                        "source": "dynamic_variable",
                        "value": "system__caller_id",
                        "schema": {"type": "string"},
                    }
                ],
                "headers": [
                    {
                        "name": "X-Api-Key",
                        "value_type": "secret",
                        "credential": {"secret_id": secret["id"], "version": 1},
                    }
                ],
            },
        },
        if_match=draft.etag,
    )
    print("pre_call tool:", tool.body["id"])

    mcp = client.create_mcp_server(
        name="BharatPay Ledger MCP",
        url=mcp_url if mcp_url.startswith("https://") else "https://example.com/mcp",
        resource_key="bharatpay-mcp",
        credential={"secret_id": mcp_secret["id"], "version": 1},
    )
    server_id = mcp.body["id"]
    client.discover_mcp_tools(server_id)
    tools = client.list_mcp_tools(server_id)
    print("mcp tools:", [t["name"] for t in tools.get("items", [])])

    draft = client.get_draft(agent_id)
    # Attach first discovered tool as example (live needs schema_digest from discover)
    for remote in tools.get("items", [])[:1]:
        draft = client.get_draft(agent_id)
        client.create_agent_tool(
            agent_id,
            {
                "name": remote["name"],
                "description": remote["name"],
                "kind": "mcp",
                "side_effect": "none",
                "retry_posture": "none",
                "definition": {
                    "server_id": server_id,
                    "remote_tool_name": remote["name"],
                    "schema_digest": remote.get("schema_digest", "d1"),
                },
            },
            if_match=draft.etag,
        )

    draft = client.get_draft(agent_id)
    client.patch_draft(
        agent_id,
        {
            "default_tools": {
                "transfer": {
                    "enabled": True,
                    "destinations": [
                        {
                            "label": "Fraud Desk",
                            "when_to_use": "Fraud flag or scam suspicion",
                            "target": {"kind": "e164", "e164": "+910000000001"},
                            "ring_timeout_s": 30,
                        },
                        {
                            "label": "Billing Disputes",
                            "when_to_use": "Cap exceeded or complex chargeback",
                            "target": {"kind": "e164", "e164": "+910000000002"},
                            "ring_timeout_s": 30,
                        },
                    ],
                }
            }
        },
        if_match=draft.etag,
    )

    draft = client.get_draft(agent_id)
    client.validate_draft(agent_id, {"prompt": draft.body["prompt"]}, if_match=draft.etag)
    published = client.publish_agent(agent_id, if_match=draft.etag)
    print("published:", published["live_version_id"])

    # Share link requires ETag from share-link resource; fake accepts any
    try:
        share = client.set_share_link(agent_id, enabled=True, if_match='"share-0"')
        print("share-link:", share)
    except Exception as exc:  # noqa: BLE001
        print("share-link skipped:", exc)

    print(
        json.dumps(
            {
                "agent_id": agent_id,
                "live_version_id": published["live_version_id"],
                "precall_url": f"{public}/pre-call/lookup_caller",
                "webhook_url": f"{public}/webhooks/rasen",
                "mcp_secret_id": mcp_secret["id"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
