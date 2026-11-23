from app.policy import check_refund_eligibility


def test_vip_eligible_allow():
    d = check_refund_eligibility(
        vip_tier="vip",
        fraud_flag=False,
        txn_status="failed",
        txn_amount_inr=1299,
        requested_amount_inr=1299,
        otp_verified=True,
    )
    assert d.decision == "allow"
    assert d.policy_code == "ELIGIBLE_FAILED_UPI"


def test_fraud_denied():
    d = check_refund_eligibility(
        vip_tier="standard",
        fraud_flag=True,
        txn_status="failed",
        txn_amount_inr=999,
        requested_amount_inr=999,
        otp_verified=True,
    )
    assert d.decision == "deny"
    assert d.policy_code == "FRAUD_FLAG"
    assert d.recommended_transfer == "Fraud Desk"


def test_cap_exceeded():
    d = check_refund_eligibility(
        vip_tier="standard",
        fraud_flag=False,
        txn_status="failed",
        txn_amount_inr=18500,
        requested_amount_inr=18500,
        otp_verified=True,
    )
    assert d.decision == "deny"
    assert d.policy_code == "CAP_EXCEEDED"
