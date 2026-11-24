"""Regression tests for Cultural Triangle quote, enquiry identity, and A2UI consistency (Issues 1-8)."""
from __future__ import annotations

import json
from datetime import date
from uuid import uuid4

from conftest import headers, quotes, turn
from mira import data
from mira.catalog import Card, Notice


def _send(client, trip_id: str, message: str, run_id: str | None = None):
    from mira.catalog import Turn

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
    snap = next(e["snapshot"]["turn"] for e in reversed(events) if e["type"] == "STATE_SNAPSHOT" and "turn" in e["snapshot"])
    return Turn.model_validate(snap)


def test_cultural_triangle_jan_10_consistent_across_chat_and_tour_detail(app_client):
    # 1. Chat entry point (exact natural language)
    trip_chat = app_client.post("/api/trips").json()["id"]
    out_chat = _send(
        app_client,
        trip_chat,
        "Cultural Triangle Sri Lanka Package for 4 adults and 3 children aged 7, 7, 7 on 10 January 2027",
    )
    assert not quotes(out_chat)
    notice_chat = next(c for c in out_chat.components if isinstance(c, Notice))
    assert notice_chat.outcome == "PRICE_UNAVAILABLE"
    assert notice_chat.reason_code == "hotel_rate_missing_or_ambiguous"
    assert notice_chat.tour_id == "T09"
    assert notice_chat.public_reference and notice_chat.public_reference.startswith("ENQ-")
    assert "hotel rates" in out_chat.text.lower()
    # Must NOT show Colombo (T03) or Galle Fort (T16)
    tour_cards_chat = [c.id for c in out_chat.components if isinstance(c, Card)]
    assert tour_cards_chat == ["T09"]

    # 2. Tour-detail entry point (REQUEST_QUOTE payload)
    trip_detail = app_client.post("/api/trips").json()["id"]
    payload = json.dumps({
        "type": "REQUEST_QUOTE",
        "payload": {"tourId": "T09", "date": "2027-01-10", "adults": 4, "childAges": [7, 7, 7]},
    })
    out_detail = _send(app_client, trip_detail, payload)
    assert not quotes(out_detail)
    notice_detail = next(c for c in out_detail.components if isinstance(c, Notice))
    assert notice_detail.outcome == "PRICE_UNAVAILABLE"
    assert notice_detail.reason_code == "hotel_rate_missing_or_ambiguous"
    assert notice_detail.tour_id == "T09"
    assert notice_detail.public_reference and notice_detail.public_reference.startswith("ENQ-")
    assert [c.id for c in out_detail.components if isinstance(c, Card)] == ["T09"]

    # 3. Follow-up quote on active tour (T09) never falls back to custom/unrelated tours
    trip_followup = app_client.post("/api/trips").json()["id"]
    _send(app_client, trip_followup, "@tour T09")
    out_followup = _send(app_client, trip_followup, "Quote for 4 adults and 3 children aged 7, 7, 7 on 2027-01-10")
    notice_fu = next(c for c in out_followup.components if isinstance(c, Notice))
    assert notice_fu.tour_id == "T09"
    assert notice_fu.reason_code == "hotel_rate_missing_or_ambiguous"
    assert [c.id for c in out_followup.components if isinstance(c, Card)] == ["T09"]


def test_cultural_triangle_valid_april_date_matches_workbook_across_both_entrypoints(app_client):
    expected = data.price("T09", date(2027, 4, 12), 4, [7, 7, 7], date(2026, 11, 19))
    assert int(expected["total"]) == 4530
    assert int(expected["deposit"]) == 1133

    trip_chat = app_client.post("/api/trips").json()["id"]
    out_chat = _send(
        app_client,
        trip_chat,
        "Cultural Triangle Sri Lanka Package for 4 adults and 3 children aged 7, 7, 7 on 12 April 2027",
    )
    [q_chat] = quotes(out_chat)

    trip_detail = app_client.post("/api/trips").json()["id"]
    payload = json.dumps({
        "type": "REQUEST_QUOTE",
        "payload": {"tourId": "T09", "date": "2027-04-12", "adults": 4, "childAges": [7, 7, 7]},
    })
    out_detail = _send(app_client, trip_detail, payload)
    [q_detail] = quotes(out_detail)

    assert q_chat.total == q_detail.total == 4530
    assert q_chat.deposit == q_detail.deposit == 1133
    assert q_chat.source == q_detail.source == "T09"


def test_traveller_and_staff_enquiry_reference_identity_and_idempotency(app_client):
    trip_id = app_client.post("/api/trips").json()["id"]
    payload = json.dumps({
        "type": "REQUEST_QUOTE",
        "payload": {"tourId": "T09", "date": "2027-01-10", "adults": 4, "childAges": [7, 7, 7]},
    })
    run_id = str(uuid4())
    out1 = _send(app_client, trip_id, payload, run_id=run_id)
    out2 = _send(app_client, trip_id, payload, run_id=run_id)
    assert out1.trace == out2.trace

    notice = next(c for c in out1.components if isinstance(c, Notice))
    pub_ref = notice.public_reference
    uuid_ref = str(notice.reference)
    assert pub_ref.startswith("ENQ-")
    assert pub_ref != uuid_ref

    # Both public ENQ reference and UUID resolve to the same enquiry without creating duplicates
    before_count = len(app_client.get("/api/staff/enquiries", headers=headers("staff")).json())
    by_pub = app_client.get(f"/api/enquiries/{pub_ref}").json()
    by_uuid = app_client.get(f"/api/enquiries/{uuid_ref}").json()
    assert by_pub["id"] == by_uuid["id"] == uuid_ref
    assert by_pub["reference"] == by_uuid["reference"] == pub_ref
    assert len(app_client.get("/api/staff/enquiries", headers=headers("staff")).json()) == before_count

    # Staff can search, open, and update using the exact public ENQ reference
    searched = app_client.get(f"/api/staff/enquiries?search={pub_ref}", headers=headers("staff")).json()
    assert len(searched) == 1
    assert searched[0]["id"] == uuid_ref

    detail = app_client.get(f"/api/staff/enquiries/{pub_ref}", headers=headers("staff")).json()
    assert detail["id"] == uuid_ref
    assert detail["reference"] == pub_ref
    assert detail["tour_id"] == "T09"
    assert detail["travel_date"] == "2027-01-10"
    assert detail["adults"] == 4
    assert detail["child_ages"] == [7, 7, 7]

    patch = app_client.patch(
        f"/api/staff/enquiries/{pub_ref}",
        json={"status": "in_review", "note": "Checking Hotel Suisse Peak contract"},
        headers=headers("staff"),
    )
    assert patch.status_code == 200
    assert app_client.get(f"/api/enquiries/{pub_ref}").json()["status"] == "in_review"


def test_health_exposes_revision_without_paths_or_secrets(app_client):
    h = app_client.get("/api/health").json()
    assert h["rates"] is True
    assert isinstance(h["revision"], str) and len(h["revision"]) > 0
    assert "/" not in h["revision"]
