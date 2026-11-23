from app.db import Base, SessionLocal, engine, init_db
from app.main import app
from app.models import Account, Customer, Transaction
from fastapi.testclient import TestClient


def _seed():
    init_db()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.add(
        Customer(
            id="cust_priya",
            phone_e164="+919800000001",
            name="Priya Sharma",
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
    db.commit()
    db.close()


def test_lookup_caller_get_and_post():
    _seed()
    client = TestClient(app)
    get_resp = client.get("/pre-call/lookup_caller", params={"phone": "+919800000001"})
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["customer_id"] == "cust_priya"
    assert body["name"] == "Priya Sharma"
    assert body["vip_tier"] == "vip"

    post_resp = client.post(
        "/pre-call/lookup_caller",
        json={"phone": "+919800000001"},
    )
    assert post_resp.status_code == 200
    assert post_resp.json()["customer_id"] == "cust_priya"


def test_lookup_caller_miss_fail_open():
    _seed()
    client = TestClient(app)
    resp = client.get("/pre-call/lookup_caller", params={"phone": "+910000000000"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["pre_call_miss"] is True
    assert body["customer_id"] is None
