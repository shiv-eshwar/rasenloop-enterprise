import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.db import Base, SessionLocal, engine, init_db
from app.models import Account, AuthSession, Customer, Transaction
from app.services import ledger
from app.services.reconciler import reconcile_effect


@pytest.fixture()
def db():
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
    token = "auth_test_token"
    session.add(
        AuthSession(
            id="otp_1",
            customer_id="cust_priya",
            otp_code="123456",
            verified_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            auth_token=token,
        )
    )
    session.commit()
    yield session, token
    session.close()


def test_double_effect_id_no_double_money(db):
    session, token = db
    effect_id = f"eff_{uuid.uuid4().hex[:8]}"
    first = ledger.execute_refund(
        session,
        customer_id="cust_priya",
        txn_id="txn_55",
        amount_inr=1299,
        effect_id=effect_id,
        auth_token=token,
    )
    second = ledger.execute_refund(
        session,
        customer_id="cust_priya",
        txn_id="txn_55",
        amount_inr=1299,
        effect_id=effect_id,
        auth_token=token,
    )
    assert first["status"] == "executed"
    assert second["idempotent_replay"] is True
    assert first["refund_id"] == second["refund_id"]


def test_auth_required_without_otp(db):
    session, _token = db
    with pytest.raises(ledger.LedgerError) as exc:
        ledger.execute_refund(
            session,
            customer_id="cust_priya",
            txn_id="txn_55",
            amount_inr=1299,
            effect_id="eff_noauth",
            auth_token=None,
        )
    assert exc.value.code == "auth_required"


def test_indeterminate_reconcile_without_row(db):
    session, token = db
    effect_id = "eff_partial"
    with pytest.raises(ledger.LedgerError):
        ledger.execute_refund(
            session,
            customer_id="cust_priya",
            txn_id="txn_55",
            amount_inr=1299,
            effect_id=effect_id,
            auth_token=token,
            partial_write=True,
        )
    result = reconcile_effect(session, effect_id)
    assert result["status"] == "failed"
    assert result.get("safe_to_retry_with_new_effect_id") is True
