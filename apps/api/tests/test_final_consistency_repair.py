"""Consistency tests for Colombo City Tour pricing, staff metrics, cross-user privacy, and legacy rows."""
import json
from uuid import uuid4

from mira import store
from mira.main import _enrich_enquiry
from mira.store import published_records
from tests.conftest import headers


def _send_agent(client, trip_id: str, content: str):
    """Post a turn to ``/api/agent`` for ``trip_id`` and return the ``turn`` snapshot dict."""
    run = str(uuid4())
    resp = client.post(
        "/api/agent",
        params={"trip_id": trip_id},
        json={
            "threadId": trip_id,
            "runId": run,
            "messages": [{"id": run, "role": "user", "content": content}],
            "state": {},
            "tools": [],
            "context": [],
            "forwardedProps": {},
        },
    )
    resp.raise_for_status()
    events = [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]
    return next(e["snapshot"]["turn"] for e in reversed(events) if e["type"] == "STATE_SNAPSHOT" and "turn" in e["snapshot"])


def test_1_2_3_colombo_city_tour_exact_price_and_tour_preservation(app_client):
    """Verify T03 REQUEST_QUOTE computes exact USD total/deposit for 2 adults + 4 children."""
    trip = app_client.post("/api/trips").json()["id"]
    payload = json.dumps({
        "type": "REQUEST_QUOTE",
        "payload": {"tourId": "T03", "date": "2027-01-10", "adults": 2, "childAges": [7, 7, 7, 7]},
    })
    turn_res = _send_agent(app_client, trip, payload)
    breakdowns = [c for c in turn_res["components"] if c["type"] == "PriceBreakdown"]
    assert len(breakdowns) == 1
    q = breakdowns[0]["quote"]
    assert q["source"] == "T03"
    assert q["title"] == "Colombo City Tour"
    assert q["total"] == 245
    assert q["deposit"] == 245
    assert q["balance"] == 0
    assert q["adults"] == 2
    assert q["ages"] == [7, 7, 7, 7]

    tour_cards = [c for c in turn_res["components"] if c["type"] == "TourCard"]
    assert [c["id"] for c in tour_cards] == ["T03"]
    assert not any(c["type"] == "EnquiryNotice" for c in turn_res["components"])


def test_4_5_6_9_staff_metrics_contactability_metadata_and_dedup(app_client):
    """Verify staff overview counts, contact attachment, pagination headers, and quote history preservation."""
    # Create 2 enquiries: 1 anonymous verified quote (recalculated twice), 1 contactable missing-rate enquiry
    t1 = app_client.post("/api/trips").json()["id"]
    _send_agent(app_client, t1, "@trip T03 2027-01-10 2 7,7,7,7")
    _send_agent(app_client, t1, "@trip T03 2027-01-10 3 7,7")

    t2 = app_client.post("/api/trips").json()["id"]
    miss = _send_agent(app_client, t2, "@trip T10 2027-01-10 2 -")
    notice = next(c for c in miss["components"] if c["type"] == "EnquiryNotice")
    e2_id = notice["reference"]

    # Attach real contact details to e2_id
    c_res = app_client.post(
        "/api/enquiries/contact",
        json={
            "enquiry_id": e2_id,
            "trip_id": t2,
            "name": "Nimali Silva",
            "email": "nimali@example.test",
            "phone": "+94 77 555 1234",
            "tour_id": "T10",
            "date": "2027-01-10",
            "adults": 2,
            "child_ages": [],
            "notes": "Need twin beds",
        },
    )
    assert c_res.status_code == 200

    staff_h = headers("staff")
    # Paginated list (limit=1) must not alter overview counts
    page1 = app_client.get("/api/staff/enquiries", params={"limit": 1, "offset": 0}, headers=staff_h)
    assert page1.status_code == 200
    assert len(page1.json()) == 1
    assert int(page1.headers["X-Total-Count"]) == 2

    all_rows = app_client.get("/api/staff/enquiries", headers=staff_h).json()
    assert len(all_rows) == 2

    anon_row = next(r for r in all_rows if r["tour_id"] == "T03")
    lead_row = next(r for r in all_rows if r["tour_id"] == "T10")

    assert anon_row["is_contactable"] is False
    assert anon_row["traveller_name"] == "Guest traveller"
    assert anon_row["adults"] == 3
    assert anon_row["child_ages"] == [7, 7]
    assert anon_row["travel_date"] == "2027-01-10"
    assert anon_row["reference"].startswith("ENQ-")

    assert lead_row["is_contactable"] is True
    assert lead_row["traveller_name"] == "Nimali Silva"
    assert lead_row["traveller_email"] == "nimali@example.test"

    ov = app_client.get("/api/staff/dashboard/overview", headers=staff_h).json()
    assert ov["total_enquiries"] == 2
    assert ov["open_enquiries"] == 2
    assert ov["contactable_enquiries"] == 1
    assert ov["missing_rate_enquiries"] == 1
    assert ov["unassigned_enquiries"] == 2

    # Verify both historical quotes for t1 are preserved in quotes table
    with store.db() as conn:
        q_cnt = conn.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]
        assert q_cnt == 2


def test_7_10_traveller_dashboard_and_cross_user_privacy(app_client):
    """Verify traveller overview counts and strict isolation between Traveller A and Traveller B."""
    # Register Traveller A
    r_a = app_client.post("/api/auth/register", json={
        "email": "traveller.a@example.test",
        "password": "Password123!",
        "full_name": "Traveller A",
        "phone": "",
    })
    assert r_a.status_code == 200

    trip_a = app_client.post("/api/trips").json()["id"]
    turn_a = _send_agent(app_client, trip_a, "@trip T03 2027-01-10 2 -")
    enq_a = next(c["quote"]["enquiry"] for c in turn_a["components"] if c["type"] == "PriceBreakdown")

    ov_a = app_client.get("/api/traveller/overview").json()
    assert ov_a["total_quotes"] == 1
    assert ov_a["total_enquiries"] == 1
    assert ov_a["active_enquiries"] == 1
    assert ov_a["total_trips"] == 1
    assert len(ov_a["quotes"]) == 1
    assert len(ov_a["trips"]) == 1
    assert ov_a["trips"][0]["tour"] == "T03"

    # Logout and register Traveller B -> must NOT see Traveller A's records
    app_client.post("/api/auth/logout").raise_for_status()
    app_client.post("/api/session", json={"remember": False}).raise_for_status()
    app_client.post("/api/auth/register", json={
        "email": "traveller.b@example.test",
        "password": "Password123!",
        "full_name": "Traveller B",
        "phone": "",
    }).raise_for_status()

    ov_b = app_client.get("/api/traveller/overview").json()
    assert ov_b["total_quotes"] == 0
    assert ov_b["total_enquiries"] == 0
    assert app_client.get(f"/api/enquiries/{enq_a}").status_code == 404


def test_8_legacy_incomplete_enquiry_renders_safely(app_client):
    """Verify ``is_contactable`` is False when no actual email exists even if the DB flag was set."""
    with store.db() as conn:
        vid = str(uuid4())
        tid = str(uuid4())
        eid = str(uuid4())
        conn.execute("INSERT INTO visitors(id, remember, context) VALUES (?, 0, '{}')", (vid,))
        conn.execute(
            "INSERT INTO traces(id, visitor, run, events, result) VALUES (?, ?, ?, '[]', '{}')",
            (tid, vid, str(uuid4())),
        )
        conn.execute(
            "INSERT INTO enquiries(id, trace, quote, trip, reason, status, is_contactable) VALUES (?, ?, NULL, '{}', 'custom_or_unsupported', 'new', 1)",
            (eid, tid),
        )
        row = conn.execute("SELECT * FROM enquiries WHERE id=?", (eid,)).fetchone()
        enriched = _enrich_enquiry(conn, row, published_records(), include_traveller=True)

    # Even though stale column had is_contactable=1, no email/phone exists -> must be False
    assert enriched["is_contactable"] is False
    assert enriched["traveller_name"] == "Guest traveller"
    assert enriched["traveller_email"] == "Contact details not provided"
    assert enriched["reference"].startswith("ENQ-")
