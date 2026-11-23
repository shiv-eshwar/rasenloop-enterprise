from __future__ import annotations

from dataclasses import dataclass, field

STANDARD_AUTO_CAP_INR = 5000.0
VIP_AUTO_CAP_INR = 25000.0
ELIGIBLE_STATUSES = {"failed", "disputed_eligible"}


@dataclass
class PolicyDecision:
    decision: str  # allow | deny
    policy_code: str
    max_amount_inr: float
    requires_otp: bool
    reasons: list[str] = field(default_factory=list)
    recommended_transfer: str | None = None


def check_refund_eligibility(
    *,
    vip_tier: str,
    fraud_flag: bool,
    txn_status: str,
    txn_amount_inr: float,
    requested_amount_inr: float,
    otp_verified: bool,
) -> PolicyDecision:
    """Deterministic refund policy — LLM never owns this decision."""
    reasons: list[str] = []

    if fraud_flag:
        return PolicyDecision(
            decision="deny",
            policy_code="FRAUD_FLAG",
            max_amount_inr=0.0,
            requires_otp=False,
            reasons=["fraud_flag_set"],
            recommended_transfer="Fraud Desk",
        )

    if txn_status not in ELIGIBLE_STATUSES:
        return PolicyDecision(
            decision="deny",
            policy_code="TXN_NOT_ELIGIBLE",
            max_amount_inr=0.0,
            requires_otp=True,
            reasons=[f"status_{txn_status}"],
            recommended_transfer="Billing Disputes",
        )

    cap = VIP_AUTO_CAP_INR if vip_tier == "vip" else STANDARD_AUTO_CAP_INR
    if requested_amount_inr > txn_amount_inr + 1e-6:
        return PolicyDecision(
            decision="deny",
            policy_code="AMOUNT_EXCEEDS_TXN",
            max_amount_inr=txn_amount_inr,
            requires_otp=True,
            reasons=["requested_gt_txn"],
            recommended_transfer="Billing Disputes",
        )

    if requested_amount_inr > cap + 1e-6:
        return PolicyDecision(
            decision="deny",
            policy_code="CAP_EXCEEDED",
            max_amount_inr=cap,
            requires_otp=True,
            reasons=["above_auto_cap", f"cap_{cap:.0f}"],
            recommended_transfer="Billing Disputes",
        )

    if not otp_verified:
        # Eligibility can be pre-checked, but execute_refund still requires OTP.
        reasons.append("otp_required_before_execute")

    reasons.append("transaction_eligible")
    if vip_tier == "vip":
        reasons.append("within_vip_cap")
    else:
        reasons.append("within_standard_cap")

    return PolicyDecision(
        decision="allow",
        policy_code="ELIGIBLE_FAILED_UPI" if txn_status == "failed" else "ELIGIBLE_DISPUTE",
        max_amount_inr=requested_amount_inr,
        requires_otp=True,
        reasons=reasons,
        recommended_transfer=None,
    )
