from app.db import Base, SessionLocal, engine, init_db
from app.services.signals import classify_call


def test_grounding_unverified_promise():
    init_db()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    created = classify_call(
        db,
        call_id="call_sig_1",
        transcript_text="Agent: aapka refund ho gaya successfully",
        tool_outcomes=[],
    )
    types = {s.signal_type for s in created}
    assert "grounding_unverified_promise" in types
    db.close()


def test_indeterminate_refund_signal():
    init_db()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    created = classify_call(
        db,
        call_id="call_sig_2",
        transcript_text="checking status",
        tool_outcomes=[
            {"tool_name": "execute_refund", "state": "indeterminate", "latency_ms": 2500},
        ],
    )
    types = {s.signal_type for s in created}
    assert "indeterminate_refund" in types
    assert "tool_latency_spike" in types
    db.close()
