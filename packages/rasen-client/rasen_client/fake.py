from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass
from typing import Any

from rasen_client.transport import TransportResponse


@dataclass
class RecordedRequest:
    method: str
    path: str
    headers: dict[str, str]
    json: Any | None
    params: dict[str, Any] | None


class FakeChaosTransport:
    """In-memory Rasen API for unit tests and offline demos."""

    def __init__(self) -> None:
        self.requests: list[RecordedRequest] = []
        self.chaos: set[str] = set()
        self._idempotency: dict[str, TransportResponse] = {}
        self._agents: dict[str, dict[str, Any]] = {}
        self._drafts: dict[str, dict[str, Any]] = {}
        self._versions: dict[str, list[dict[str, Any]]] = {}
        self._secrets: dict[str, dict[str, Any]] = {}
        self._calls: dict[str, dict[str, Any]] = {}
        self._mcp_servers: dict[str, dict[str, Any]] = {}
        self._webhook_endpoints: dict[str, dict[str, Any]] = {}
        self.live_version_by_agent: dict[str, str] = {}

    def inject_chaos(self, *codes: str) -> None:
        self.chaos.update(codes)

    def clear_chaos(self) -> None:
        self.chaos.clear()

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> TransportResponse:
        headers = {k: v for k, v in (headers or {}).items()}
        self.requests.append(
            RecordedRequest(method=method, path=path, headers=headers, json=json, params=params)
        )

        if "at_capacity" in self.chaos and method == "POST" and path in {
            "/calls",
            "/agent-sessions",
        }:
            return TransportResponse(
                503,
                {
                    "error": {
                        "code": "at_capacity",
                        "message": "There is no capacity available.",
                        "details": {"reason": "workspace_limit", "active": 3, "limit": 3},
                        "retry": "retry_after",
                    }
                },
                headers={"Retry-After": "1"},
            )

        if "draft_conflict" in self.chaos and method in {"PATCH", "POST"} and "/draft" in path:
            return TransportResponse(
                409,
                {
                    "error": {
                        "code": "draft_conflict",
                        "message": "The draft has changed since it was read.",
                        "details": {
                            "expected_etag": headers.get("If-Match"),
                            "current_etag": '"rev-fresh"',
                        },
                    }
                },
            )

        idem_key = headers.get("Idempotency-Key")
        if idem_key and method in {"POST", "PUT", "PATCH", "DELETE"}:
            fingerprint = f"{method}:{path}:{idem_key}"
            if fingerprint in self._idempotency:
                prior = self._idempotency[fingerprint]
                replay_headers = dict(prior.headers)
                replay_headers["Idempotent-Replayed"] = "true"
                return TransportResponse(prior.status_code, copy.deepcopy(prior.body), replay_headers)

        response = self._dispatch(method, path, headers=headers, json=json, params=params)
        if idem_key and method in {"POST", "PUT", "PATCH", "DELETE"} and response.status_code < 500:
            fingerprint = f"{method}:{path}:{idem_key}"
            self._idempotency[fingerprint] = TransportResponse(
                response.status_code,
                copy.deepcopy(response.body),
                dict(response.headers),
            )
        return response

    def _dispatch(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str],
        json: Any | None,
        params: dict[str, Any] | None,
    ) -> TransportResponse:
        if method == "GET" and path == "/context":
            return TransportResponse(
                200,
                {
                    "workspace_id": "ws_fake",
                    "capabilities": [
                        "agents.write",
                        "agents.publish",
                        "calls.read",
                        "calls.write",
                        "tools.write",
                        "secrets.manage",
                        "secrets.read",
                        "webhooks.manage",
                        "config.read",
                        "knowledge.write",
                    ],
                },
            )

        if method == "GET" and path == "/voices":
            return TransportResponse(
                200,
                {
                    "items": [
                        {
                            "id": "voice_default",
                            "name": "Asha",
                            "is_default": True,
                            "grammatical_gender": "female",
                        }
                    ],
                    "next_cursor": None,
                },
            )

        if method == "POST" and path == "/agents":
            agent_id = f"agent_{uuid.uuid4().hex[:16]}"
            etag = f'"rev-{uuid.uuid4().hex[:8]}"'
            agent = {
                "id": agent_id,
                "name": (json or {}).get("name", "Support"),
                "resource_key": (json or {}).get("resource_key"),
                "state": "draft",
                "live_version_id": None,
            }
            draft = {
                "agent_id": agent_id,
                "revision": etag.strip('"'),
                "prompt": ((json or {}).get("initial_draft") or {}).get(
                    "prompt", "You are the support agent."
                ),
                "settings": ((json or {}).get("initial_draft") or {}).get("settings", {}),
                "default_tools": ((json or {}).get("initial_draft") or {}).get(
                    "default_tools", {"end_call": {"enabled": True}}
                ),
                "tool_ids": [],
                "variables": [],
            }
            self._agents[agent_id] = agent
            self._drafts[agent_id] = draft
            self._versions[agent_id] = []
            return TransportResponse(201, agent, headers={"ETag": etag})

        if method == "GET" and path.startswith("/agents/") and path.endswith("/draft"):
            agent_id = path.split("/")[2]
            draft = self._drafts[agent_id]
            etag = f'"{draft["revision"]}"'
            return TransportResponse(200, draft, headers={"ETag": etag})

        if method == "PATCH" and path.startswith("/agents/") and path.endswith("/draft"):
            agent_id = path.split("/")[2]
            draft = self._drafts[agent_id]
            expected = headers.get("If-Match", "").strip('"')
            if expected and expected != draft["revision"]:
                return TransportResponse(
                    409,
                    {
                        "error": {
                            "code": "draft_conflict",
                            "details": {
                                "expected_etag": headers.get("If-Match"),
                                "current_etag": f'"{draft["revision"]}"',
                            },
                        }
                    },
                )
            for key, value in (json or {}).items():
                if key == "settings" and isinstance(value, dict):
                    draft.setdefault("settings", {}).update(value)
                else:
                    draft[key] = value
            draft["revision"] = f"rev-{uuid.uuid4().hex[:8]}"
            return TransportResponse(200, draft, headers={"ETag": f'"{draft["revision"]}"'})

        if method == "POST" and path.startswith("/agents/") and path.endswith("/draft/validate"):
            return TransportResponse(
                200,
                {"valid": True, "errors": [], "warnings": [], "readiness": {"state": "ready"}},
            )

        if method == "POST" and path.startswith("/agents/") and path.endswith("/publish"):
            agent_id = path.split("/")[2]
            draft = self._drafts[agent_id]
            version_id = f"pub_{uuid.uuid4().hex[:16]}"
            version = {
                "id": version_id,
                "number": len(self._versions[agent_id]) + 1,
                "prompt": draft["prompt"],
                "settings": copy.deepcopy(draft.get("settings", {})),
            }
            self._versions[agent_id].append(version)
            self.live_version_by_agent[agent_id] = version_id
            self._agents[agent_id]["state"] = "live"
            self._agents[agent_id]["live_version_id"] = version_id
            return TransportResponse(
                200,
                {
                    "version": version,
                    "created": True,
                    "live_version_id": version_id,
                },
            )

        if method == "POST" and path.startswith("/agents/") and path.endswith("/rollback"):
            agent_id = path.split("/")[2]
            body = json or {}
            to_version = body.get("version_id")
            expected_live = body.get("expected_live_version_id")
            current = self.live_version_by_agent.get(agent_id)
            if expected_live and current != expected_live:
                return TransportResponse(
                    409,
                    {
                        "error": {
                            "code": "conflict",
                            "details": {
                                "reason": "live_version_changed",
                                "current_live_version_id": current,
                            },
                        }
                    },
                )
            self.live_version_by_agent[agent_id] = to_version
            self._agents[agent_id]["live_version_id"] = to_version
            return TransportResponse(
                200,
                {
                    "from_version_id": current,
                    "to_version_id": to_version,
                    "warnings": [],
                },
            )

        if method == "GET" and path.startswith("/agents/") and path.count("/") == 2:
            agent_id = path.split("/")[2]
            return TransportResponse(200, self._agents[agent_id])

        if method == "POST" and path == "/secrets":
            secret_id = f"sec_{uuid.uuid4().hex[:16]}"
            secret = {
                "id": secret_id,
                "name": (json or {}).get("name"),
                "resource_key": (json or {}).get("resource_key"),
                "purpose": (json or {}).get("purpose"),
                "state": "active",
                "latest_version": 1,
            }
            self._secrets[secret_id] = {
                **secret,
                "versions": {1: {"state": "active", "value": (json or {}).get("value")}},
            }
            return TransportResponse(201, secret)

        if (
            method == "POST"
            and "/secrets/" in path
            and path.endswith("/revoke")
        ):
            # /secrets/{id}/versions/{v}/revoke
            parts = path.strip("/").split("/")
            secret_id = parts[1]
            version = int(parts[3])
            secret = self._secrets[secret_id]
            secret["versions"][version]["state"] = "revoked"
            return TransportResponse(
                200,
                {
                    "secret_id": secret_id,
                    "version": version,
                    "state": "revoked",
                    "revoke_reason": (json or {}).get("reason", "requested"),
                },
            )

        if method == "POST" and path == "/mcp-servers":
            server_id = f"mcp_{uuid.uuid4().hex[:16]}"
            server = {
                "id": server_id,
                "name": (json or {}).get("name"),
                "url": (json or {}).get("url"),
                "discovery_state": "not_discovered",
                "revision": f"rev-{uuid.uuid4().hex[:8]}",
            }
            self._mcp_servers[server_id] = server
            return TransportResponse(201, server, headers={"ETag": f'"{server["revision"]}"'})

        if method == "POST" and path.startswith("/mcp-servers/") and path.endswith("/discover"):
            server_id = path.split("/")[2]
            server = self._mcp_servers[server_id]
            server["discovery_state"] = "discovered"
            tools = [
                {"name": "get_customer_ledger", "schema_digest": "d1"},
                {"name": "check_refund_eligibility", "schema_digest": "d2"},
                {"name": "execute_refund", "schema_digest": "d3"},
                {"name": "create_escalation_ticket", "schema_digest": "d4"},
                {"name": "schedule_callback", "schema_digest": "d5"},
            ]
            server["tools"] = tools
            return TransportResponse(200, {"state": "discovered", "tools": tools})

        if method == "GET" and path.startswith("/mcp-servers/") and path.endswith("/tools"):
            server_id = path.split("/")[2]
            tools = self._mcp_servers[server_id].get("tools", [])
            return TransportResponse(200, {"items": tools, "next_cursor": None})

        if method == "POST" and path.startswith("/agents/") and path.endswith("/tools"):
            agent_id = path.split("/")[2]
            tool_id = f"tool_{uuid.uuid4().hex[:16]}"
            draft = self._drafts[agent_id]
            draft["tool_ids"].append(tool_id)
            draft["revision"] = f"rev-{uuid.uuid4().hex[:8]}"
            tool = {
                "id": tool_id,
                "agent_id": agent_id,
                "configuration": {
                    "name": (json or {}).get("name"),
                    "kind": (json or {}).get("kind"),
                    "timing": (json or {}).get("timing", "during_call"),
                },
            }
            return TransportResponse(201, tool, headers={"ETag": f'"{draft["revision"]}"'})

        if method == "POST" and path == "/agent-sessions":
            call_id = f"call_{uuid.uuid4().hex[:16]}"
            agent_id = (json or {}).get("agent_id")
            version = self.live_version_by_agent.get(agent_id, "pub_unknown")
            expected = (json or {}).get("expected_version_id")
            if expected and expected != version:
                return TransportResponse(
                    409,
                    {
                        "error": {
                            "code": "conflict",
                            "details": {
                                "reason": "live_version_mismatch",
                                "current_live_version_id": version,
                            },
                        }
                    },
                )
            call = {
                "call_id": call_id,
                "agent_id": agent_id,
                "published_version_id": version,
                "state": "admitted",
                "direction": (json or {}).get("direction", "inbound"),
                "websocket_url": f"wss://fake.invalid/calls/{call_id}/ws/token",
                "expires_at": "2099-01-01T00:00:00Z",
            }
            self._calls[call_id] = {
                **call,
                "end_reason": None,
                "transcript": [],
                "tool_outcomes": [],
            }
            return TransportResponse(201, call)

        if method == "GET" and path.startswith("/calls/") and path.count("/") == 2:
            call_id = path.split("/")[2]
            return TransportResponse(200, self._calls.get(call_id, {"id": call_id, "state": "unknown"}))

        if method == "GET" and path.endswith("/tool-outcomes"):
            call_id = path.split("/")[2]
            call = self._calls.get(call_id, {})
            return TransportResponse(
                200,
                {
                    "state": "ready",
                    "items": call.get("tool_outcomes", []),
                    "next_cursor": None,
                    "poll_after_seconds": None,
                },
            )

        if method == "PUT" and path.endswith("/share-link"):
            return TransportResponse(
                200,
                {
                    "enabled": (json or {}).get("enabled", True),
                    "token": "share_fake_token" if (json or {}).get("enabled") else None,
                    "url": "https://app.rasen.ai/share/fake",
                },
                headers={"ETag": '"share-1"'},
            )

        if method == "POST" and path == "/webhook-endpoints":
            endpoint_id = f"whep_{uuid.uuid4().hex[:16]}"
            endpoint = {
                "id": endpoint_id,
                "url": (json or {}).get("url"),
                "events": (json or {}).get("events", []),
                "state": "enabled",
                "secret": "whsec_" + uuid.uuid4().hex,
                "revision": "1",
            }
            self._webhook_endpoints[endpoint_id] = endpoint
            return TransportResponse(201, endpoint, headers={"ETag": '"1"'})

        if method == "GET" and path == "/usage":
            return TransportResponse(
                200,
                {
                    "state": "measured",
                    "items": [
                        {
                            "component": "stt",
                            "unit": "second",
                            "quantity": 12.0,
                            "events": 1,
                        }
                    ],
                    "next_cursor": None,
                },
            )

        return TransportResponse(
            404,
            {"error": {"code": "not_found", "message": f"Fake route missing: {method} {path}"}},
        )
