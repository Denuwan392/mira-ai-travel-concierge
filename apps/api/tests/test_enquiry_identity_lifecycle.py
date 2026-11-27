"""Regression tests for enquiry identity deduplication, tour switching, and contact attachment."""
import json
from uuid import uuid4

from mira import store
from mira.main import _enrich_enquiry
from mira.store import published_records
from tests.conftest import headers


def _send_turn(client, trip_id: str, content: str, run_id: str | None = None):
    """Post a turn to ``/api/agent`` for ``trip_id`` and return the ``turn`` snapshot dict."""
    rid = run_id or str(uuid4())
    resp = client.post(
        "/api/agent",
        params={"trip_id": trip_id},
        json={
            "threadId": trip_id,
            "runId": rid,
            "messages": [{"id": rid, "role": "user", "content": content}],
            "state": {},
            "tools": [],
            "context": [],
            "forwardedProps": {},
        },
    )
    resp.raise_for_status()
    events = [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]
    return next(e["snapshot"]["turn"] for e in reversed(events) if e["type"] == "STATE_SNAPSHOT" and "turn" in e["snapshot"])


def test_enquiry_identity_lifecycle_and_no_cross_tour_overwrite(app_client):
    """Verify same-tour quote recalculation reuses enquiry while tour switches create distinct enquiries."""
    app_client.post("/api/auth/register", json={
        "email": "lifecycle@example.test",
        "password": "Password123!",
        "full_name": "Lifecycle Tester",
        "phone": "",
    }).raise_for_status()

    trip_id = app_client.post("/api/trips").json()["id"]

    # 1. Submit a new enquiry (T03 verified quote) -> exactly 1 record created
    run_1 = str(uuid4())
    t1 = _send_turn(app_client, trip_id, "@trip T03 2027-01-10 2 -", run_id=run_1)
    q1 = next(c["quote"] for c in t1["components"] if c["type"] == "PriceBreakdown")
    e1_id = q1["enquiry"]

    # 3. Repeat exact same runId -> idempotent, still 1 enquiry and 1 quote
    _send_turn(app_client, trip_id, "@trip T03 2027-01-10 2 -", run_id=run_1)
    with store.db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM enquiries").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM quotes").fetchone()[0] == 1

    # 5. Recalculate pricing on SAME tour T03 -> preserves quote history (2 quotes) and reuses same enquiry (1 enquiry)
    t2 = _send_turn(app_client, trip_id, "@trip T03 2027-01-10 4 -")
    q2 = next(c["quote"] for c in t2["components"] if c["type"] == "PriceBreakdown")
    assert q2["enquiry"] == e1_id
    assert q2["id"] != q1["id"]
    with store.db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM enquiries").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM quotes").fetchone()[0] == 2

    # 4a. Switch to a DIFFERENT tour (T01) on same trip -> must NOT overwrite T03 enquiry
    t3 = _send_turn(app_client, trip_id, "@trip T01 2027-01-10 2 -")
    q3 = next(c["quote"] for c in t3["components"] if c["type"] == "PriceBreakdown")
    assert q3["enquiry"] != e1_id

    # 4b. Switch across different missing-rate tours (T09 -> T10) -> distinct enquiries
    t4 = _send_turn(app_client, trip_id, "@trip T09 2027-01-10 2 7")
    e_t09 = next(c["reference"] for c in t4["components"] if c["type"] == "EnquiryNotice")
    t5 = _send_turn(app_client, trip_id, "@trip T10 2027-01-10 2 -")
    e_t10 = next(c["reference"] for c in t5["components"] if c["type"] == "EnquiryNotice")
    assert e_t09 != e_t10

    # 4c. Switch across different custom requests -> distinct enquiries
    t6 = _send_turn(app_client, trip_id, "Create a custom 5-day trip across Kandy and Ella")
    e_c1 = next(c["reference"] for c in t6["components"] if c["type"] == "EnquiryNotice")
    t7 = _send_turn(app_client, trip_id, "Create a custom 4-day trip across Galle and Mirissa")
    e_c2 = next(c["reference"] for c in t7["components"] if c["type"] == "EnquiryNotice")
    assert e_c1 != e_c2

    # 2, 6, 7, 9. Retrieve via confirmation endpoint & dashboard; lookup creates zero extra records
    ov = app_client.get("/api/traveller/overview").json()
    match_enq = next(e for e in ov["enquiries"] if e["id"] == e1_id)
    pub_ref = match_enq["reference"]
    assert pub_ref.startswith("ENQ-")
    assert match_enq["created"].endswith("Z")
    assert match_enq["updated_at"].endswith("Z")

    with store.db() as conn:
        before_cnt = conn.execute("SELECT COUNT(*) FROM enquiries").fetchone()[0]

    pub_by_uuid = app_client.get(f"/api/enquiries/{e1_id}").json()
    pub_by_ref = app_client.get(f"/api/enquiries/{pub_ref}").json()
    assert pub_by_uuid["id"] == pub_by_ref["id"] == e1_id
    assert pub_by_uuid["reference"] == pub_by_ref["reference"] == pub_ref
    assert pub_by_uuid["tour_name"] == "Colombo City Tour"
    assert pub_by_uuid["adults"] == 4
    assert pub_by_uuid["human_reason"] == "Verified quote saved"

    with store.db() as conn:
        after_cnt = conn.execute("SELECT COUNT(*) FROM enquiries").fetchone()[0]
        assert after_cnt == before_cnt

    # 8. Staff finds the same enquiry by public reference (using separate staff client without traveller cookie)
    from fastapi.testclient import TestClient
    from mira.main import app
    with TestClient(app) as staff_client:
        staff_res = staff_client.get("/api/staff/enquiries", params={"search": pub_ref}, headers=headers("staff"))
        assert staff_res.status_code == 200
        staff_rows = staff_res.json()
        assert len(staff_rows) == 1
        assert staff_rows[0]["id"] == e1_id
        assert staff_rows[0]["reference"] == pub_ref


def test_historical_incomplete_record_safe_rendering(app_client):
    """Verify ``_enrich_enquiry`` handles legacy rows with empty ``trip`` JSON gracefully."""
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
            "INSERT INTO enquiries(id, trace, quote, trip, reason, status) VALUES (?, ?, NULL, '{}', 'custom_or_unsupported', 'new')",
            (eid, tid),
        )
        row = conn.execute("SELECT * FROM enquiries WHERE id=?", (eid,)).fetchone()
        enriched = _enrich_enquiry(conn, row, published_records(), include_traveller=True)

    assert enriched["adults"] is None
    assert enriched["travel_date"] is None
    assert enriched["tour_id"] is None
    assert enriched["human_reason"] == "Custom itinerary requires specialist confirmation"
    assert enriched["traveller_name"] == "Guest traveller"


def test_direct_nl_quotation_saves_single_enquiry_and_attaches_contact(app_client):
    """Natural-language quote requests route directly to pricing in one turn without duplicate enquiries."""
    for prompt in (
        "Quote Sigiriya for 2 adults on January 10, 2027",
        "Sigiriya, January 10, 2027, 2 adults",
    ):
        trip = app_client.post("/api/trips").json()["id"]
        turn = _send_turn(app_client, trip, prompt)
        breakdowns = [c for c in turn["components"] if c["type"] == "PriceBreakdown"]
        assert len(breakdowns) == 1, f"Expected direct PriceBreakdown for {prompt!r}, got {turn['components']}"
        q = breakdowns[0]["quote"]
        assert q["source"] == "T01"
        assert q["total"] == 315
        assert q["deposit"] == 315
        assert q["enquiry_reference"].startswith("ENQ-")

        # Attaching contact details updates the existing enquiry rather than creating a duplicate
        contact_res = app_client.post(
            "/api/enquiries/contact",
            json={
                "enquiry_id": q["enquiry"],
                "trip_id": trip,
                "name": "Kasun Perera",
                "email": "kasun@example.com",
            },
        )
        assert contact_res.status_code == 200
        assert contact_res.json()["reference"] == q["enquiry_reference"]
        staff_enqs = [
            e for e in app_client.get("/api/staff/enquiries", headers=headers("staff")).json()
            if e["reference"] == q["enquiry_reference"]
        ]
        assert len(staff_enqs) == 1
        assert staff_enqs[0]["contact_name"] == "Kasun Perera"
