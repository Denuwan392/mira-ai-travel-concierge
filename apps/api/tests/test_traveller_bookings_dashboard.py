"""Traveller My Bookings dashboard, simulated balance payment, and cancellation synchronization tests."""
import json
from decimal import Decimal
from uuid import uuid4

from mira.store import db


def _register_and_login(client, email: str, password: str = "StrongPass123!"):
    client.post("/api/session", json={})
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Test Traveller"},
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


def _send(client, trip_id: str, content: str):
    run = str(uuid4())
    r = client.post(
        f"/api/agent?trip_id={trip_id}",
        json={
            "threadId": trip_id,
            "runId": run,
            "state": {},
            "messages": [{"role": "user", "id": run, "content": content}],
            "tools": [],
            "context": [],
            "forwardedProps": {},
        },
    )
    r.raise_for_status()
    events = [json.loads(line[6:]) for line in r.text.splitlines() if line.startswith("data: ")]
    assert events[-1]["type"] == "RUN_FINISHED", events[-1]
    snapshots = [e["snapshot"] for e in events if e.get("type") == "STATE_SNAPSHOT"]
    return next(s["turn"] for s in reversed(snapshots) if "turn" in s)


def test_booking_dashboard_balance_payment_idempotency_and_cancellation(app_client):
    """Full lifecycle: quote T09 -> mock book -> My Bookings -> failed/partial/balance pay -> preview cancel -> confirm -> staff sync."""
    _register_and_login(app_client, f"trav_{uuid4().hex[:8]}@example.com")
    tid = app_client.post("/api/trips").json()["id"]
    turn = _send(app_client, tid, "Quote Cultural Triangle Sri Lanka Package for 2 adults on 2027-04-12")
    pb = next(c for c in turn["components"] if c["type"] == "PriceBreakdown")
    q = pb["quote"]
    qid = q["id"]
    total = Decimal(str(q["total"]))
    deposit = Decimal(str(q["deposit"]))
    assert deposit < total  # Multi-day tour has 25% deposit

    bk = app_client.post("/api/bookings/mock", json={"quote": qid, "scenario": "success"})
    assert bk.status_code == 200
    ref = bk.json()["reference"]

    # 1. Inspect My Bookings
    res = app_client.get("/api/traveller/bookings?filter=all")
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["upcoming_confirmed"] == 1
    assert data["summary"]["fully_paid"] == 0
    assert Decimal(data["summary"]["outstanding_balance_total"]) == total - deposit
    item = data["bookings"][0]
    assert item["booking_reference"] == ref
    assert item["payment_status"] == "deposit_paid"
    assert item["balance_due_date"] == "2027-03-13"  # 30 days before 2027-04-12 per P01
    assert len(item["payments"]) == 1

    # 2. Validation guards: negative, overpayment, failed payment
    assert app_client.post(f"/api/bookings/{ref}/pay", json={"amount": "-10"}).status_code == 400
    assert app_client.post(f"/api/bookings/{ref}/pay", json={"amount": str(total)}).status_code == 400
    r_fail = app_client.post(f"/api/bookings/{ref}/pay", json={"amount": "100", "scenario": "failed"})
    assert r_fail.status_code == 200
    assert r_fail.json()["status"] == "failed"
    assert Decimal(r_fail.json()["paid_amount"]) == deposit

    # 3. Pay remaining balance with idempotency key
    rem = str(total - deposit)
    idem = f"bal-{ref}"
    r_pay1 = app_client.post(f"/api/bookings/{ref}/pay", json={"amount": rem, "scenario": "success", "idempotency_key": idem})
    assert r_pay1.status_code == 200
    assert r_pay1.json()["idempotent"] is False
    assert Decimal(r_pay1.json()["outstanding_balance"]) == Decimal("0")

    r_pay2 = app_client.post(f"/api/bookings/{ref}/pay", json={"amount": rem, "scenario": "success", "idempotency_key": idem})
    assert r_pay2.status_code == 200
    assert r_pay2.json()["idempotent"] is True

    # Paying again with a new key after fully paid -> 409
    assert app_client.post(f"/api/bookings/{ref}/pay", json={"amount": "10", "idempotency_key": "new-key"}).status_code == 409

    # 4. Verify fully paid in My Bookings
    res_paid = app_client.get("/api/traveller/bookings?filter=all").json()
    assert res_paid["summary"]["fully_paid"] == 1
    assert Decimal(res_paid["summary"]["outstanding_balance_total"]) == Decimal("0")
    assert res_paid["bookings"][0]["payment_status"] == "fully_paid"

    # 5. Two-phase cancellation calculates refund from full paid_amount (total - USD 50 admin fee per P02 >=30d)
    assert app_client.post(f"/api/bookings/{ref}/cancel").status_code == 409
    prev = app_client.post(f"/api/bookings/{ref}/cancel/preview")
    assert prev.status_code == 200
    assert Decimal(prev.json()["paid_amount"]) == total
    assert Decimal(prev.json()["refund_amount"]) == total - Decimal("50")

    conf = app_client.post(f"/api/bookings/{ref}/cancel", json={"reason": "traveller_requested"})
    assert conf.status_code == 200
    assert conf.json()["status"] == "cancelled"
    assert Decimal(conf.json()["refund_amount"]) == total - Decimal("50")

    # Cannot pay a cancelled booking
    assert app_client.post(f"/api/bookings/{ref}/pay", json={"amount": "10"}).status_code == 409

    # Cancelled filter & overview reflect cancellation
    res_canc = app_client.get("/api/traveller/bookings?filter=cancelled").json()
    assert res_canc["summary"]["cancelled"] == 1
    assert res_canc["bookings"][0]["payment_status"] == "simulated_refund_completed"


def test_booking_cross_account_isolation_and_named_nl_cancellation(app_client):
    """Cross-account booking access returns 404; 'Cancel my Galle booking' resolves directly."""
    _register_and_login(app_client, f"owner_{uuid4().hex[:8]}@example.com")
    t1 = app_client.post("/api/trips").json()["id"]
    turn1 = _send(app_client, t1, "Quote Sigiriya and Minneriya Day Tour from Kandy for 2 adults on 2027-04-12")
    q1 = next(c for c in turn1["components"] if c["type"] == "PriceBreakdown")["quote"]["id"]
    b1 = app_client.post("/api/bookings/mock", json={"quote": q1}).json()["reference"]

    t2 = app_client.post("/api/trips").json()["id"]
    turn2 = _send(app_client, t2, "Quote Galle Fort Walking Tour for 2 adults on 2027-04-15")
    q2 = next(c for c in turn2["components"] if c["type"] == "PriceBreakdown")["quote"]["id"]
    b2 = app_client.post("/api/bookings/mock", json={"quote": q2}).json()["reference"]
    assert b1 != b2

    # Natural language "Cancel my Galle booking" resolves directly to b2
    t_cancel = _send(app_client, t2, "Cancel my Galle booking")
    prev = next(c for c in t_cancel["components"] if c["type"] == "CancellationPreview")
    assert prev["booking_reference"] == b2

    # Switch to a different user -> cannot read or pay or cancel b1/b2
    app_client.post("/api/auth/logout")
    _register_and_login(app_client, f"other_{uuid4().hex[:8]}@example.com")
    assert app_client.get("/api/traveller/bookings").json()["bookings"] == []
    assert app_client.post(f"/api/bookings/{b1}/pay", json={"amount": "10"}).status_code == 404
    assert app_client.post(f"/api/bookings/{b1}/cancel/preview").status_code == 404
