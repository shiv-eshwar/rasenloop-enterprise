import uuid
from datetime import UTC, datetime, timedelta

from app.db import Base, SessionLocal, engine, init_db
from app.models import Account, AuthSession, Customer, Effect, Transaction
from app.services import ledger
from app.services.reconciler import reconcile_effect, reconcile_pending


def _db():
    init_db()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    session.add(
        Customer(
            id="cust_priya",
            phone_e164="+919800000001",
            name="Priya",
            vip_tier="vip",
            fraud_flag=False,
        )
    )
    session.add(Account(id="acc_priya", customer_id="cust_priya", available_balance_inr=1000))
    session.add(
        Transaction(
            id="txn_55",
            account_id="acc_priya",
            channel="upi",
            amount_inr=1299,
            status="failed",
            merchant="RailYatri",
        )
    )
    session.add(
        AuthSession(
            id="otp_1",
            customer_id="cust_priya",
            otp_code="123456",
            verified_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            auth_token="auth_ok",
        )
    )
    session.commit()
    return session


def test_reconcile_indeterminate_without_refund_is_failed():
    session = _db()
    effect_id = f"eff_{uuid.uuid4().hex[:8]}"
    session.add(
        Effect(
            effect_id=effect_id,
            tool_name="execute_refund",
            status="indeterminate",
            request_hash="x",
        )
    )
    session.commit()
    result = reconcile_effect(session, effect_id)
    assert result["status"] == "failed"
    assert result["safe_to_retry_with_new_effect_id"] is True
    session.close()


def test_reconcile_does_not_double_refund():
    session = _db()
    effect_id = f"eff_{uuid.uuid4().hex[:8]}"
    first = ledger.execute_refund(
        session,
        customer_id="cust_priya",
        txn_id="txn_55",
        amount_inr=1299,
        effect_id=effect_id,
        auth_token="auth_ok",
    )
    assert first["status"] == "executed"
    # Reconcile executed effect is a noop — no second money movement
    bal_before = session.get(Account, "acc_priya").available_balance_inr
    result = reconcile_effect(session, effect_id)
    assert result.get("noop") is True
    bal_after = session.get(Account, "acc_priya").available_balance_inr
    assert bal_before == bal_after
    session.close()


def test_reconcile_pending_batch():
    session = _db()
    session.add(
        Effect(
            effect_id="eff_pending_1",
            tool_name="execute_refund",
            status="indeterminate",
        )
    )
    session.commit()
    results = reconcile_pending(session)
    assert any(r["effect_id"] == "eff_pending_1" for r in results)
    session.close()
