from __future__ import annotations


def assert_no_refund_without_effect(tool_outcomes: list[dict], transcript: str) -> tuple[bool, str]:
    promised = any(
        p in transcript.lower()
        for p in ["refund ho gaya", "refunded successfully", "refund is done"]
    )
    executed = any(
        o.get("tool_name") == "execute_refund" and o.get("state") == "succeeded"
        for o in tool_outcomes
    )
    if promised and not executed:
        return False, "Transcript promised refund without successful execute_refund"
    return True, "ok"


def assert_policy_denial_no_refund(tool_outcomes: list[dict]) -> tuple[bool, str]:
    executed = any(
        o.get("tool_name") == "execute_refund" and o.get("state") == "succeeded"
        for o in tool_outcomes
    )
    if executed:
        return False, "Refund executed when scenario expected denial"
    return True, "ok"


def assert_effect_unique(effect_ids: list[str]) -> tuple[bool, str]:
    if len(effect_ids) != len(set(effect_ids)):
        return False, "Duplicate effect_ids observed"
    return True, "ok"
