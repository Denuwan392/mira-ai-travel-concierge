import json
from uuid import uuid4

from mira import store
from tests.conftest import headers, turn


def test_end_to_end_staff_enquiry_and_contact_workflow(app_client):
    # 1. Create a trip and select Cultural Triangle Tour (T16) + price / specialist handoff
    trip = app_client.post("/api/trips").json()["id"]

    # Turn 1: select T16
    r1 = app_client.post(
        "/api/agent",
        params={"trip_id": trip},
        json={
            "threadId": trip,
            "runId": str(uuid4()),
            "messages": [{"id": str(uuid4()), "role": "user", "content": "Cultural Triangle Tour"}],
            "state": {},
            "tools": [],
            "context": [],
            "forwardedProps": {},
        },
    )
    r1.raise_for_status()

    # Turn 2: request price for 2027-01-10 for 2 adults and 1 child aged 7
    r2 = app_client.post(
        "/api/agent",
        params={"trip_id": trip},
        json={
            "threadId": trip,
            "runId": str(uuid4()),
            "messages": [{"id": str(uuid4()), "role": "user", "content": "@trip T16 2027-01-10 2 7"}],
            "state": {},
            "tools": [],
            "context": [],
            "forwardedProps": {},
        },
    )
    r2.raise_for_status()

    # Turn 3: recalculate with 3 adults on the same trip -> should NOT create a duplicate enquiry
    r3 = app_client.post(
        "/api/agent",
        params={"trip_id": trip},
        json={
            "threadId": trip,
            "runId": str(uuid4()),
            "messages": [{"id": str(uuid4()), "role": "user", "content": "@trip T16 2027-01-10 3 7"}],
            "state": {},
            "tools": [],
            "context": [],
            "forwardedProps": {},
        },
    )
    r3.raise_for_status()

    with store.db() as conn:
        enq_rows = conn.execute(
            "SELECT DISTINCT e.id FROM enquiries e JOIN trip_turns t ON t.trace = e.trace WHERE t.trip = ?",
            (trip,),
        ).fetchall()
        assert len(enq_rows) == 1
        enq_id = enq_rows[0]["id"]

    # 2. Unauthorized access checks
    assert app_client.get("/api/staff/enquiries").status_code == 401
    assert app_client.get(f"/api/staff/enquiries/{enq_id}").status_code == 401
    assert app_client.patch(f"/api/staff/enquiries/{enq_id}", json={"status": "contacted"}).status_code == 401

    # 3. Traveller submits contact details via /api/enquiries/contact
    contact_res = app_client.post(
        "/api/enquiries/contact",
        json={
            "enquiry_id": enq_id,
            "trip_id": trip,
            "name": "Eleanor Vance",
            "email": "eleanor.vance@example.test",
            "phone": "+44 7700 900123",
            "tour_id": "T16",
            "tour_title": "Cultural Triangle Tour",
            "date": "2027-01-10",
            "adults": 3,
            "child_ages": [7],
            "notes": "Vegetarian meals preferred",
        },
    )
    assert contact_res.status_code == 200
    contact_data = contact_res.json()
    assert contact_data["id"] == enq_id
    assert contact_data["reference"].startswith("ENQ-")
    assert contact_data["is_contactable"] is True
    ref_code = contact_data["reference"]

    # Verify PII did NOT leak into LLM trace events
    with store.db() as conn:
        tr = conn.execute("SELECT events FROM traces WHERE id = (SELECT trace FROM enquiries WHERE id = ?)", (enq_id,)).fetchone()
        assert "eleanor.vance@example.test" not in tr["events"]
        assert "7700 900123" not in tr["events"]

    # 4. Staff lists, searches, and opens enquiry
    staff_hdrs = headers("staff")
    list_res = app_client.get("/api/staff/enquiries", params={"contactable": "1", "search": "Eleanor"}, headers=staff_hdrs)
    assert list_res.status_code == 200
    assert int(list_res.headers["X-Total-Count"]) >= 1
    items = list_res.json()
    assert len(items) == 1
    assert items[0]["traveller_name"] == "Eleanor Vance"
    assert items[0]["traveller_email"] == "eleanor.vance@example.test"
    assert items[0]["is_contactable"] is True

    detail = app_client.get(f"/api/staff/enquiries/{enq_id}", headers=staff_hdrs).json()
    assert detail["reference"] == ref_code
    assert detail["special_requests"] == "Vegetarian meals preferred"
    assert detail["tour_id"] == "T16"

    # 5. Staff assigns to an active staff user, adds a note, sets follow-up date, updates status
    with store.db() as conn:
        staff_uid = str(uuid4())
        conn.execute(
            "INSERT INTO users(id, email, password_hash, full_name, role, status) VALUES (?,?,?,?,?,?)",
            (staff_uid, "specialist@ceyloncompass.test", "hash", "Priya Specialist", "staff", "active"),
        )

    # Note containing PII should still be rejected
    bad_note = app_client.patch(
        f"/api/staff/enquiries/{enq_id}",
        headers=staff_hdrs,
        json={"status": "contacted", "note": "Call eleanor@example.test"},
    )
    assert bad_note.status_code == 422

    patch_res = app_client.patch(
        f"/api/staff/enquiries/{enq_id}",
        headers=staff_hdrs,
        json={
            "status": "in_review",
            "note": "Checked seasonal hotel availability for January.",
            "assigned_to": staff_uid,
            "follow_up_date": "2026-12-01",
        },
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "in_review"
    assert patch_res.json()["assigned_name"] == "Priya Specialist"
    assert patch_res.json()["follow_up_date"] == "2026-12-01"

    # Verify persistence after refresh
    refreshed = app_client.get(f"/api/staff/enquiries/{enq_id}", headers=staff_hdrs).json()
    assert refreshed["status"] == "in_review"
    assert refreshed["assigned_to"] == staff_uid
    assert refreshed["assigned_name"] == "Priya Specialist"
    assert refreshed["follow_up_date"] == "2026-12-01"
    assert len(refreshed["notes"]) == 1
    assert refreshed["notes"][0]["body"] == "Checked seasonal hotel availability for January."

    # 6. Overview metrics reflect authoritative DB state
    overview = app_client.get("/api/staff/dashboard/overview", headers=staff_hdrs).json()
    assert overview["open_enquiries"] >= 1
    assert overview["contactable_enquiries"] >= 1

    # 7. Traveller views their own enquiry via public reference without finance/notes leakage
    pub = app_client.get(f"/api/enquiries/{ref_code}")
    assert pub.status_code == 200
    pub_data = pub.json()
    assert pub_data["status"] == "in_review"
    assert pub_data["reference"] == ref_code
    assert "finance" not in pub_data
    assert "notes" not in pub_data
    assert "cost_lkr" not in json.dumps(pub_data)
