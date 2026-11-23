from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class TransportResponse:
    status_code: int
    body: Any
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def etag(self) -> str | None:
        for key, value in self.headers.items():
            if key.lower() == "etag":
                return value
        return None

    @property
    def idempotent_replayed(self) -> bool:
        for key, value in self.headers.items():
            if key.lower() == "idempotent-replayed":
                return value.lower() == "true"
        return False


class Transport(Protocol):
    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> TransportResponse: ...


class LiveHttpTransport:
    """Real Rasen HTTP transport."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0) -> None:
        import httpx

        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> TransportResponse:
        response = self._client.request(
            method,
            path,
            headers=headers,
            json=json,
            params=params,
        )
        try:
            body: Any = response.json() if response.content else None
        except Exception:
            body = response.text
        return TransportResponse(
            status_code=response.status_code,
            body=body,
            headers={k: v for k, v in response.headers.items()},
        )

    def close(self) -> None:
        self._client.close()
