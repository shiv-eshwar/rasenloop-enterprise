#!/usr/bin/env python3
"""Seed BharatPay demo customers and transactions."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "backend"))

from app.db import SessionLocal, init_db
from app.models import Account, Customer, Incident, Transaction


def seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        if db.get(Customer, "cust_priya"):
            print("Seed already present")
            return

        customers = [
            Customer(
                id="cust_priya",
                phone_e164="+919800000001",
                name="Priya Sharma",
                vip_tier="vip",
                fraud_flag=False,
                language_preference="hinglish",
            ),
            Customer(
                id="cust_rahul",
                phone_e164="+919800000002",
                name="Rahul Verma",
                vip_tier="standard",
                fraud_flag=False,
                language_preference="hinglish",
            ),
            Customer(
                id="cust_fraud",
                phone_e164="+919800000003",
                name="Amit FraudFlag",
                vip_tier="standard",
                fraud_flag=True,
                language_preference="en",
            ),
            Customer(
                id="cust_otp",
                phone_e164="+919800000004",
                name="Neha OTP",
                vip_tier="standard",
                fraud_flag=False,
                language_preference="hinglish",
            ),
        ]
        for c in customers:
            db.add(c)

        accounts = [
            Account(id="acc_priya", customer_id="cust_priya", available_balance_inr=15420.55),
            Account(id="acc_rahul", customer_id="cust_rahul", available_balance_inr=2200.00),
            Account(id="acc_fraud", customer_id="cust_fraud", available_balance_inr=500.00),
            Account(id="acc_otp", customer_id="cust_otp", available_balance_inr=8800.00),
        ]
        for a in accounts:
            db.add(a)

        txns = [
            Transaction(
                id="txn_55",
                account_id="acc_priya",
                channel="upi",
                amount_inr=1299.00,
                status="failed",
                merchant="RailYatri",
            ),
            Transaction(
                id="txn_big",
                account_id="acc_rahul",
                channel="card",
                amount_inr=18500.00,
                status="failed",
                merchant="Apple Store",
            ),
            Transaction(
                id="txn_fraud",
                account_id="acc_fraud",
                channel="upi",
                amount_inr=999.00,
                status="failed",
                merchant="Unknown Merchant",
            ),
            Transaction(
                id="txn_otp",
                account_id="acc_otp",
                channel="upi",
                amount_inr=450.00,
                status="failed",
                merchant="Swiggy",
            ),
        ]
        for t in txns:
            db.add(t)

        db.add(
            Incident(
                id="inc_9",
                customer_id="cust_priya",
                summary="UPI failed debit under review",
                status="open",
            )
        )
        db.commit()
        print("Seeded 4 customers, accounts, transactions")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
