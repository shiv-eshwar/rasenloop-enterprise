"""Shared JSON-shaped schemas (non-ORM) for signals and eval reports."""

from __future__ import annotations

from typing import Any, TypedDict


class EvalScenarioResult(TypedDict, total=False):
    id: str
    name: str
    severity: str
    passed: bool
    checks: list[dict[str, Any]]
    chaos: str | None


class EvalReport(TypedDict, total=False):
    transport_mode: str
    passed: bool
    scenarios: list[EvalScenarioResult]
    blocker_failures: list[str]
    rollback: dict[str, Any] | None
