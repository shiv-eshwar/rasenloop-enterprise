from enum import StrEnum


class SignalType(StrEnum):
    GROUNDING_UNVERIFIED_PROMISE = "grounding_unverified_promise"
    POLICY_BYPASS_ATTEMPT = "policy_bypass_attempt"
    TOOL_LATENCY_SPIKE = "tool_latency_spike"
    STT_ARGUMENT_CORRUPTION = "stt_argument_corruption"
    ESCALATION_LOOP = "escalation_loop"
    PRE_CALL_MISS = "pre_call_miss"
    INDETERMINATE_REFUND = "indeterminate_refund"
    AUTH_FAILURE_SPAM = "auth_failure_spam"
    KILL_SWITCH_ENGAGED = "kill_switch_engaged"


class SignalSeverity(StrEnum):
    BLOCKER = "blocker"
    CRITICAL = "critical"
    HIGH = "high"
    MED = "med"
    LOW = "low"
