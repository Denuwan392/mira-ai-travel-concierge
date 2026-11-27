"""MIRA V2.2 Context-Aware Cancellation and Booking Management acceptance tests (Scenarios A-L)."""
from __future__ import annotations

import json
from datetime import date, datetime, time, timezone
from decimal import Decimal
from uuid import uuid4

from mira.auth import hash_password
from mira.cancellation import POLICY_VERSION, evaluate_cancellation
from mira.catalog import PublicQuote, Turn
from mira.data import published
from mira.store import db


def _send(client, trip_id: str, message: str, run_id: str | None = None) -> Turn:
    run_id = run_id or str(uuid4())
    resp = client.post(
        "/api/agent",
        params={"trip_id": trip_id},
        json={
            "threadId": trip_id,
            "runId": run_id,
            "state": {},
            "tools": [],
            "context": [],
            "messages": [{"id": run_id, "role": "user", "content": message}],
            "forwardedProps": {},
        },
    )
    resp.raise_for_status()
    events = [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]
    snap = next(e["snapshot"]["turn"] for e in reversed(events) if e.get("type") == "STATE_SNAPSHOT" and "turn" in e["snapshot"])
    return Turn.model_validate(snap)


def _book_tour(client, trip_id: str, tour_id: str = "T01", travel_date: str = "2027-02-10", adults: int = 2) -> tuple[str, str]:
    payload = json.dumps({"type": "REQUEST_QUOTE", "payload": {"tourId": tour_id, "date": travel_date, "adults": adults, "childAges": []}})
    t_q = _send(client, trip_id, payload)
    q = next(c.quote for c in t_q.components if c.type == "PriceBreakdown")
    r_b = client.post("/api/bookings/mock", json={"quote": str(q.id), "scenario": "success"})
    assert r_b.status_code == 200
    return str(q.id), r_b.json()["reference"]


def test_scenario_a_and_i_confirmed_booking_cancel_and_idempotency(app_client):
    """Scenarios A & I: Quote -> mock book -> 'I want to cancel this.' -> preview -> confirm -> idempotent repeat."""
    trip_id = app_client.post("/api/trips").json()["id"]
    quote_id, booking_ref = _book_tour(app_client, trip_id, "T01", "2027-02-10", 2)

    t_prev = _send(app_client, trip_id, "I want to cancel this.")
    prev = next(c for c in t_prev.components if c.type == "CancellationPreview")
    assert prev.target_type == "booking"
    assert prev.target_id == quote_id
    assert prev.refund_amount == "USD 315"
    assert prev.requires_confirmation is True

    # Confirm cancellation
    t_conf = _send(app_client, trip_id, "Yes, go ahead.")
    st = next(c for c in t_conf.components if c.type == "CancellationStatus")
    assert st.status == "cancelled"
    assert st.refund_status == "simulated_completed"
    assert st.refund_amount == "USD 315"

    with db() as conn:
        b = conn.execute("SELECT status, refund_amount, refund_status, policy_version FROM bookings WHERE quote=?", (quote_id,)).fetchone()
        assert b["status"] == "cancelled"
        assert b["refund_amount"] == "315"
        assert b["refund_status"] == "simulated_completed"
        assert b["policy_version"] == POLICY_VERSION
        reqs_before = conn.execute("SELECT COUNT(*) FROM cancellation_requests WHERE booking_id=?", (quote_id,)).fetchone()[0]

    # Scenario I: Idempotent repeat via REST endpoint does not create duplicate cancellation or refund
    r_dup = app_client.post(f"/api/bookings/{booking_ref}/cancel")
    assert r_dup.status_code == 200
    assert r_dup.json()["idempotent"] is True
    with db() as conn:
        reqs_after = conn.execute("SELECT COUNT(*) FROM cancellation_requests WHERE booking_id=?", (quote_id,)).fetchone()[0]
        assert reqs_after == reqs_before == 1


def test_scenario_b_decline_cancellation_keeps_booking(app_client):
    """Scenario B: Request cancellation -> 'Actually, keep my booking.' -> booking remains confirmed."""
    trip_id = app_client.post("/api/trips").json()["id"]
    quote_id, _ = _book_tour(app_client, trip_id, "T01", "2027-02-10", 2)

    _send(app_client, trip_id, "I want to cancel this.")
    t_keep = _send(app_client, trip_id, "Actually, keep my booking.")
    st = next(c for c in t_keep.components if c.type == "CancellationStatus")
    assert st.status == "kept"

    with db() as conn:
        b = conn.execute("SELECT status FROM bookings WHERE quote=?", (quote_id,)).fetchone()
        assert b["status"] == "confirmed"


def test_scenario_c_and_d_policy_and_hypothetical_refund_no_mutation(app_client):
    """Scenarios C & D: Policy inquiry and hypothetical refund never mutate booking."""
    trip_id = app_client.post("/api/trips").json()["id"]
    quote_id, _ = _book_tour(app_client, trip_id, "T01", "2027-02-10", 2)

    t_pol = _send(app_client, trip_id, "What is your cancellation policy?")
    assert "P02" in t_pol.sources

    t_ref = _send(app_client, trip_id, "How much would I get back if I cancelled?")
    assert "315" in t_ref.text
    assert "nothing has been cancelled" in t_ref.text.lower()

    with db() as conn:
        assert conn.execute("SELECT status FROM bookings WHERE quote=?", (quote_id,)).fetchone()["status"] == "confirmed"


def test_scenario_e_multiple_bookings_requires_clarification(app_client):
    """Scenario E: Two confirmed bookings -> 'Cancel my booking.' asks which booking, never guesses."""
    t1 = app_client.post("/api/trips").json()["id"]
    _book_tour(app_client, t1, "T01", "2027-02-10", 2)
    t2 = app_client.post("/api/trips").json()["id"]
    _book_tour(app_client, t2, "T04", "2027-03-10", 2)

    out = _send(app_client, t2, "Cancel my booking.")
    assert "multiple active bookings" in out.text.lower()
    assert not any(c.type == "CancellationStatus" for c in out.components)


def test_scenario_f_unbooked_itinerary_no_invented_booking(app_client):
    """Scenario F: Unbooked custom itinerary -> 'Cancel this trip.' offers plan abandonment, no fake refund."""
    trip_id = app_client.post("/api/trips").json()["id"]
    _send(app_client, trip_id, "Plan a 5-day trip to Mirissa.")
    t_prev = _send(app_client, trip_id, "Cancel this trip.")
    prev = next(c for c in t_prev.components if c.type == "CancellationPreview")
    assert prev.target_type == "plan"
    assert prev.paid_amount == "USD 0"
    assert prev.refund_amount == "USD 0"


def test_scenario_g_context_interruption_resumes_pending_cancellation(app_client):
    """Scenario G: Cancel preview -> policy question -> 'Yes, go ahead.' executes original cancellation."""
    trip_id = app_client.post("/api/trips").json()["id"]
    quote_id, _ = _book_tour(app_client, trip_id, "T01", "2027-02-10", 2)

    _send(app_client, trip_id, "Cancel my booking.")
    t_pol = _send(app_client, trip_id, "What is your refund policy?")
    assert "P02" in t_pol.sources

    t_conf = _send(app_client, trip_id, "Yes, go ahead.")
    st = next(c for c in t_conf.components if c.type == "CancellationStatus")
    assert st.status == "cancelled"
    with db() as conn:
        assert conn.execute("SELECT status FROM bookings WHERE quote=?", (quote_id,)).fetchone()["status"] == "cancelled"


def test_scenario_h_unauthorized_cross_user_cancellation_rejected(app_client):
    """Scenario H: User B cannot cancel User A's booking."""
    with db() as conn:
        for email in ("user-a@example.com", "user-b@example.com"):
            conn.execute(
                "INSERT INTO users(id, email, password_hash, full_name, role, status, phone, preferences) VALUES (?, ?, ?, ?, 'traveller', 'active', '', '{}')",
                (str(uuid4()), email, hash_password("Password123!"), email),
            )

    app_client.post("/api/auth/login", json={"email": "user-a@example.com", "password": "Password123!"})
    t_a = app_client.post("/api/trips").json()["id"]
    quote_a, ref_a = _book_tour(app_client, t_a, "T01", "2027-02-10", 2)

    app_client.post("/api/auth/login", json={"email": "user-b@example.com", "password": "Password123!"})
    r_forbid = app_client.post(f"/api/bookings/{ref_a}/cancel")
    assert r_forbid.status_code == 404

    with db() as conn:
        assert conn.execute("SELECT status FROM bookings WHERE quote=?", (quote_a,)).fetchone()["status"] == "confirmed"


def test_scenario_j_policy_boundaries_decimal():
    """Scenario J: Exact P02 time boundaries for Day tours (48h Asia/Colombo) and Multi-day tours + legacy + unknown departure time."""
    from zoneinfo import ZoneInfo
    sl_tz = ZoneInfo("Asia/Colombo")
    recs = published()
    q_day = PublicQuote(id=uuid4(), source="T01", title="T01", date=date(2027, 2, 10), adults=2, ages=[], total=315, deposit=315, balance=0)
    # T01 has authoritative pick-up at 5:30 am Asia/Colombo -> 48h before is 2027-02-08 05:30
    ev_48h = evaluate_cancellation(recs["T01"], q_day, {"created": "2026-11-20"}, now_dt=datetime(2027, 2, 8, 5, 30, tzinfo=sl_tz))
    assert ev_48h.refund_amount == Decimal("315")
    # 1 minute past 48h cutoff -> 0 refund
    ev_47h = evaluate_cancellation(recs["T01"], q_day, {"created": "2026-11-20"}, now_dt=datetime(2027, 2, 8, 5, 31, tzinfo=sl_tz))
    assert ev_47h.refund_amount == Decimal("0")

    # T04 has NO published departure time -> within 48h boundary window (2 days out) escalates to staff
    q_t04 = PublicQuote(id=uuid4(), source="T04", title="T04", date=date(2027, 2, 10), adults=2, ages=[], total=180, deposit=180, balance=0)
    ev_t04_boundary = evaluate_cancellation(recs["T04"], q_t04, {"created": "2026-11-20"}, now_dt=datetime(2027, 2, 8, 9, 0, tzinfo=sl_tz))
    assert ev_t04_boundary.escalate_to_staff is True

    q_multi = PublicQuote(id=uuid4(), source="T09", title="T09", date=date(2027, 4, 12), adults=2, ages=[], total=2965, deposit=742, balance=2223)
    # 30 days before -> full deposit minus USD 50 = 692
    ev_30d = evaluate_cancellation(recs["T09"], q_multi, {"created": "2026-11-20"}, now_dt=datetime(2027, 3, 13, 9, 0, tzinfo=sl_tz))
    assert ev_30d.refund_amount == Decimal("692")
    # 29 days before -> 50% of 742 = 371.00
    ev_29d = evaluate_cancellation(recs["T09"], q_multi, {"created": "2026-11-20"}, now_dt=datetime(2027, 3, 14, 9, 0, tzinfo=sl_tz))
    assert ev_29d.refund_amount == Decimal("371.00")
    # 7 days before -> 0
    ev_7d = evaluate_cancellation(recs["T09"], q_multi, {"created": "2026-11-20"}, now_dt=datetime(2027, 4, 5, 9, 0, tzinfo=sl_tz))
    assert ev_7d.refund_amount == Decimal("0")
    # Pre-Nov 1 2026 booking -> escalate to staff
    ev_old = evaluate_cancellation(recs["T09"], q_multi, {"created": "2026-10-15"}, now_dt=datetime(2027, 3, 1, 9, 0, tzinfo=sl_tz))
    assert ev_old.escalate_to_staff is True


def test_audit_direct_cancel_endpoint_requires_preview(app_client):
    """Audit #4: POST /api/bookings/{ref}/cancel cannot bypass Phase 1 preview."""
    trip_id = app_client.post("/api/trips").json()["id"]
    _, booking_ref = _book_tour(app_client, trip_id, "T01", "2027-02-10", 2)
    r_bypass = app_client.post(f"/api/bookings/{booking_ref}/cancel")
    assert r_bypass.status_code == 409

    # After preview, cancellation succeeds
    r_prev = app_client.post(f"/api/bookings/{booking_ref}/cancel/preview")
    assert r_prev.status_code == 200
    r_ok = app_client.post(f"/api/bookings/{booking_ref}/cancel")
    assert r_ok.status_code == 200
    assert r_ok.json()["status"] == "cancelled"


def test_audit_migration_0007_historical_bookings(tmp_path, monkeypatch):
    """Audit #9: Migration 0007 upgrades a pre-0007 DB containing historical bookings without data loss."""
    import sqlite3
    from pathlib import Path
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine
    import mira.store as store

    hist_db = tmp_path / "historical.sqlite3"
    alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
    script_loc = Path(__file__).resolve().parents[1] / "mira" / "migrations"
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("script_location", str(script_loc))
    engine = create_engine(f"sqlite:///{hist_db}")
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "0006_enquiry_contact_fields")
    with sqlite3.connect(hist_db) as conn:
        conn.execute("INSERT INTO visitors(id, remember) VALUES ('v-hist', 1)")
        conn.execute("INSERT INTO traces(id, visitor, run, events, result) VALUES ('tr-hist', 'v-hist', 'r-hist', '[]', '{}')")
        conn.execute("INSERT INTO quotes(id, visitor, trace, public, internal) VALUES ('q-hist', 'v-hist', 'tr-hist', '{}', '{}')")
        conn.execute("INSERT INTO bookings(quote, id) VALUES ('q-hist', 'b-hist')")

    monkeypatch.setattr(store, "DB", hist_db)
    store.init()
    with sqlite3.connect(hist_db) as conn:
        row = conn.execute("SELECT id, status, refund_status, version FROM bookings WHERE quote='q-hist'").fetchone()
        assert row == ("b-hist", "confirmed", "none", 0)


def test_scenario_k_session_lifecycle_cancel_recovery(app_client):
    """Scenario K: Request cancellation -> logout -> login same user -> confirm pending cancellation."""
    with db() as conn:
        conn.execute(
            "INSERT INTO users(id, email, password_hash, full_name, role, status, phone, preferences) VALUES (?, ?, ?, ?, 'traveller', 'active', '', '{}')",
            (str(uuid4()), "scen-k@example.com", hash_password("Password123!"), "Scenario K"),
        )
    app_client.post("/api/auth/login", json={"email": "scen-k@example.com", "password": "Password123!"})
    trip_id = app_client.post("/api/trips").json()["id"]
    quote_id, _ = _book_tour(app_client, trip_id, "T01", "2027-02-10", 2)
    _send(app_client, trip_id, "Cancel my booking.")

    # Logout and login again (simulating session rotation/refresh)
    app_client.post("/api/auth/logout")
    app_client.post("/api/auth/login", json={"email": "scen-k@example.com", "password": "Password123!"})

    t_conf = _send(app_client, trip_id, "Yes, go ahead.")
    st = next(c for c in t_conf.components if c.type == "CancellationStatus")
    assert st.status == "cancelled"
    with db() as conn:
        assert conn.execute("SELECT status FROM bookings WHERE quote=?", (quote_id,)).fetchone()["status"] == "cancelled"
