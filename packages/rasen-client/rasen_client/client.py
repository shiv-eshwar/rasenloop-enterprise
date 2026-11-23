from __future__ import annotations

import uuid
from typing import Any

from rasen_client.transport import Transport, TransportResponse


class RasenError(Exception):
    def __init__(self, status_code: int, body: Any) -> None:
        self.status_code = status_code
        self.body = body
        error = (body or {}).get("error") if isinstance(body, dict) else None
        code = error.get("code") if isinstance(error, dict) else "unknown"
        message = error.get("message") if isinstance(error, dict) else str(body)
        super().__init__(f"Rasen {status_code} {code}: {message}")

    @property
    def code(self) -> str | None:
        if isinstance(self.body, dict):
            error = self.body.get("error")
            if isinstance(error, dict):
                return error.get("code")
        return None


class RasenClient:
    """Small typed client over a Transport (live or fake)."""

    def __init__(self, transport: Transport) -> None:
        self.transport = transport
        self._last_idempotency_keys: dict[str, str] = {}

    @staticmethod
    def new_idempotency_key() -> str:
        return str(uuid.uuid4())

    def _raise_for_status(self, response: TransportResponse) -> TransportResponse:
        if response.status_code >= 400:
            raise RasenError(response.status_code, response.body)
        return response

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        if_match: str | None = None,
        persist_key_name: str | None = None,
    ) -> TransportResponse:
        headers: dict[str, str] = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
            if persist_key_name:
                self._last_idempotency_keys[persist_key_name] = idempotency_key
        if if_match:
            headers["If-Match"] = if_match
        response = self.transport.request(
            method,
            path,
            headers=headers or None,
            json=json,
            params=params,
        )
        return self._raise_for_status(response)

    def get_persisted_idempotency_key(self, name: str) -> str | None:
        return self._last_idempotency_keys.get(name)

    def get_context(self) -> dict[str, Any]:
        return self.request("GET", "/context").body

    def list_voices(self, agent_id: str | None = None) -> dict[str, Any]:
        params = {"agent_id": agent_id} if agent_id else None
        return self.request("GET", "/voices", params=params).body

    def create_agent(
        self,
        *,
        name: str,
        resource_key: str,
        initial_draft: dict[str, Any] | None = None,
        description: str | None = None,
        idempotency_key: str | None = None,
    ) -> TransportResponse:
        key = idempotency_key or self.new_idempotency_key()
        payload: dict[str, Any] = {"name": name, "resource_key": resource_key}
        if description:
            payload["description"] = description
        if initial_draft:
            payload["initial_draft"] = initial_draft
        return self.request(
            "POST",
            "/agents",
            json=payload,
            idempotency_key=key,
            persist_key_name="create_agent",
        )

    def get_agent(self, agent_id: str) -> dict[str, Any]:
        return self.request("GET", f"/agents/{agent_id}").body

    def get_draft(self, agent_id: str) -> TransportResponse:
        return self.request("GET", f"/agents/{agent_id}/draft")

    def patch_draft(
        self,
        agent_id: str,
        patch: dict[str, Any],
        *,
        if_match: str,
        idempotency_key: str | None = None,
    ) -> TransportResponse:
        key = idempotency_key or self.new_idempotency_key()
        return self.request(
            "PATCH",
            f"/agents/{agent_id}/draft",
            json=patch,
            idempotency_key=key,
            if_match=if_match,
            persist_key_name="patch_draft",
        )

    def validate_draft(
        self,
        agent_id: str,
        patch: dict[str, Any],
        *,
        if_match: str,
    ) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/agents/{agent_id}/draft/validate",
            json=patch,
            if_match=if_match,
        ).body

    def publish_agent(
        self,
        agent_id: str,
        *,
        if_match: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        key = idempotency_key or self.new_idempotency_key()
        return self.request(
            "POST",
            f"/agents/{agent_id}/publish",
            idempotency_key=key,
            if_match=if_match,
            persist_key_name="publish_agent",
        ).body

    def rollback_agent(
        self,
        agent_id: str,
        *,
        version_id: str,
        expected_live_version_id: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        key = idempotency_key or self.new_idempotency_key()
        return self.request(
            "POST",
            f"/agents/{agent_id}/rollback",
            json={
                "version_id": version_id,
                "expected_live_version_id": expected_live_version_id,
            },
            idempotency_key=key,
            persist_key_name="rollback_agent",
        ).body

    def create_secret(
        self,
        *,
        purpose: str,
        name: str,
        resource_key: str,
        value: str,
        material_kind: str = "api_key",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        key = idempotency_key or self.new_idempotency_key()
        return self.request(
            "POST",
            "/secrets",
            json={
                "purpose": purpose,
                "name": name,
                "resource_key": resource_key,
                "value": value,
                "material_kind": material_kind,
            },
            idempotency_key=key,
            persist_key_name="create_secret",
        ).body

    def revoke_secret_version(
        self,
        secret_id: str,
        version: int,
        *,
        reason: str = "compromised",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        key = idempotency_key or self.new_idempotency_key()
        return self.request(
            "POST",
            f"/secrets/{secret_id}/versions/{version}/revoke",
            json={"reason": reason},
            idempotency_key=key,
            persist_key_name="revoke_secret",
        ).body

    def create_mcp_server(
        self,
        *,
        name: str,
        url: str,
        resource_key: str,
        auth: str = "bearer",
        credential: dict[str, Any] | None = None,
        transport: str = "streamable_http",
        idempotency_key: str | None = None,
    ) -> TransportResponse:
        key = idempotency_key or self.new_idempotency_key()
        payload: dict[str, Any] = {
            "name": name,
            "url": url,
            "resource_key": resource_key,
            "auth": auth,
            "transport": transport,
        }
        if credential:
            payload["credential"] = credential
        return self.request(
            "POST",
            "/mcp-servers",
            json=payload,
            idempotency_key=key,
            persist_key_name="create_mcp_server",
        )

    def discover_mcp_tools(
        self,
        server_id: str,
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        key = idempotency_key or self.new_idempotency_key()
        return self.request(
            "POST",
            f"/mcp-servers/{server_id}/discover",
            idempotency_key=key,
            persist_key_name="discover_mcp",
        ).body

    def list_mcp_tools(self, server_id: str) -> dict[str, Any]:
        return self.request("GET", f"/mcp-servers/{server_id}/tools").body

    def create_agent_tool(
        self,
        agent_id: str,
        tool: dict[str, Any],
        *,
        if_match: str,
        idempotency_key: str | None = None,
    ) -> TransportResponse:
        key = idempotency_key or self.new_idempotency_key()
        return self.request(
            "POST",
            f"/agents/{agent_id}/tools",
            json=tool,
            idempotency_key=key,
            if_match=if_match,
            persist_key_name="create_agent_tool",
        )

    def create_agent_session(
        self,
        *,
        agent_id: str,
        direction: str = "inbound",
        expected_version_id: str | None = None,
        media: dict[str, Any] | None = None,
        metadata: dict[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        key = idempotency_key or self.new_idempotency_key()
        payload: dict[str, Any] = {"agent_id": agent_id, "direction": direction}
        if expected_version_id:
            payload["expected_version_id"] = expected_version_id
        if media:
            payload["media"] = media
        if metadata:
            payload["metadata"] = metadata
        return self.request(
            "POST",
            "/agent-sessions",
            json=payload,
            idempotency_key=key,
            persist_key_name="create_agent_session",
        ).body

    def get_call(self, call_id: str) -> dict[str, Any]:
        return self.request("GET", f"/calls/{call_id}").body

    def list_call_tool_outcomes(self, call_id: str) -> dict[str, Any]:
        return self.request("GET", f"/calls/{call_id}/tool-outcomes").body

    def set_share_link(
        self,
        agent_id: str,
        *,
        enabled: bool,
        if_match: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        key = idempotency_key or self.new_idempotency_key()
        return self.request(
            "PUT",
            f"/agents/{agent_id}/share-link",
            json={"enabled": enabled},
            idempotency_key=key,
            if_match=if_match,
            persist_key_name="share_link",
        ).body

    def create_webhook_endpoint(
        self,
        *,
        url: str,
        events: list[str],
        description: str = "RasenLoop",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        key = idempotency_key or self.new_idempotency_key()
        return self.request(
            "POST",
            "/webhook-endpoints",
            json={"url": url, "events": events, "description": description},
            idempotency_key=key,
            persist_key_name="create_webhook",
        ).body

    def list_usage(self, **params: Any) -> dict[str, Any]:
        return self.request("GET", "/usage", params=params or None).body
