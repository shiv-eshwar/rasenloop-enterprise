"""Lightweight response aliases used by demos and tests."""

from __future__ import annotations

from typing import Any, TypedDict


class AgentSummary(TypedDict, total=False):
    id: str
    name: str
    state: str
    live_version_id: str | None
    resource_key: str | None


class RollbackReceipt(TypedDict, total=False):
    from_version_id: str
    to_version_id: str
    warnings: list[Any]
