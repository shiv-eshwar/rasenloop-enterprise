import importlib.util
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "apps" / "backend"
MCP_TOOLS = ROOT / "apps" / "mcp-server" / "app" / "tools.py"

sys.path.insert(0, str(BACKEND))

from app.db import Base, SessionLocal, engine, init_db  # noqa: E402
from app.models import Account, AuthSession, Customer, Transaction  # noqa: E402

spec = importlib.util.spec_from_file_location("rasenloop_mcp_tools", MCP_TOOLS)
assert spec and spec.loader
_mcp_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_mcp_tools)
call_tool = _mcp_tools.call_tool


def setup_module():
    init_db()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.add(
        Customer(
            id="cust_priya",
            phone_e164="+919800000001",
            name="Priya",
            vip_tier="vip",
            fraud_flag=False,
        )
    )
    db.add(Account(id="acc_priya", customer_id="cust_priya", available_balance_inr=1000))
    db.add(
        Transaction(
            id="txn_55",
            account_id="acc_priya",
            channel="upi",
            amount_inr=1299,
            status="failed",
            merchant="RailYatri",
        )
    )
    db.add(
        AuthSession(
            id="otp_1",
            customer_id="cust_priya",
            otp_code="123456",
            verified_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            auth_token="auth_ok",
        )
    )
    db.commit()
    db.close()


def test_ledger_and_eligibility():
    ledger = call_tool("get_customer_ledger", {"customer_id": "cust_priya"})
    assert ledger["customer_id"] == "cust_priya"
    decision = call_tool(
        "check_refund_eligibility",
        {
            "customer_id": "cust_priya",
            "txn_id": "txn_55",
            "requested_amount_inr": "1299.00",
            "auth_token": "auth_ok",
        },
    )
    assert decision["decision"] == "allow"


def test_execute_refund_idempotent():
    effect_id = f"eff_{uuid.uuid4().hex[:8]}"
    first = call_tool(
        "execute_refund",
        {
            "customer_id": "cust_priya",
            "txn_id": "txn_55",
            "amount_inr": "1299.00",
            "effect_id": effect_id,
            "auth_token": "auth_ok",
        },
    )
    second = call_tool(
        "execute_refund",
        {
            "customer_id": "cust_priya",
            "txn_id": "txn_55",
            "amount_inr": "1299.00",
            "effect_id": effect_id,
            "auth_token": "auth_ok",
        },
    )
    assert first["refund_id"] == second["refund_id"]
    assert second.get("idempotent_replay") is True
